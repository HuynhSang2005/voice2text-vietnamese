import asyncio
import json
import logging
import uuid
from typing import List
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.core.manager import manager
from app.core.database import get_session, engine
from app.core.config import get_settings
from app.models.schema import TranscriptionLog
from app.models.protocols import ModelInfo, ModelStatus, SwitchModelResponse

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Speech-to-Text"])

@router.get("/api/v1/models", response_model=List[ModelInfo], summary="List available models")
async def get_models():
    """List available speech-to-text models with their capabilities."""
    return [
        ModelInfo(
            id="zipformer", 
            name="Zipformer", 
            description="Real-time streaming, optimized for Vietnamese (6000h trained)",
            workflow_type="streaming",
            expected_latency_ms=(100, 500)
        ),
    ]

@router.get("/api/v1/history", response_model=List[TranscriptionLog], summary="Get transcription history")
async def get_history(
    session: AsyncSession = Depends(get_session),
    page: int = 1,
    limit: int = 50,
    search: str = None,
    model: str = None,
    min_latency: float = None,
    max_latency: float = None,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """
    Get transcription history with filtering and pagination.
    
    - **page**: Page number (1-indexed)
    - **limit**: Number of items per page (max 100)
    - **search**: Search in transcription content
    - **model**: Filter by model ID
    - **min_latency/max_latency**: Filter by latency range
    - **start_date/end_date**: Filter by date range
    """
    query = select(TranscriptionLog).order_by(TranscriptionLog.created_at.desc())
    
    if search:
        query = query.where(TranscriptionLog.content.contains(search))
    if model:
        query = query.where(TranscriptionLog.model_id == model)
    if min_latency is not None:
        query = query.where(TranscriptionLog.latency_ms >= min_latency)
    if max_latency is not None:
        query = query.where(TranscriptionLog.latency_ms <= max_latency)
    if start_date:
        query = query.where(TranscriptionLog.created_at >= start_date)
    if end_date:
        query = query.where(TranscriptionLog.created_at <= end_date)
        
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await session.exec(query)
    return result.all()

@router.websocket("/ws/transcribe")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time speech transcription.
    
    Protocol:
    1. Client connects
    2. Client sends config message (optional): {"type": "config", "model": "zipformer"}
    3. Client sends binary audio data (Int16 PCM, 16kHz)
    4. Server sends transcription results: {"text": "...", "is_final": bool, "model": "..."}
    5. If content moderation enabled, server sends moderation results: 
       {"type": "moderation", "label": "CLEAN|OFFENSIVE|HATE", "confidence": float, ...}
    """
    await websocket.accept()
    
    model_name = "zipformer"  # Default
    # Session ID will be set by client via start_session message
    # Fallback to None until client sends session ID
    session_id = None
    
    # Content moderation state
    moderation_enabled = settings.ENABLE_CONTENT_MODERATION
    detector_input_q = None
    detector_output_q = None
    
    try:
        # 1. Wait for config message (Optional, or first message)
        first_msg = await websocket.receive()
        
        if "text" in first_msg:
            try:
                config = json.loads(first_msg["text"])
                if config.get("type") == "config":
                    model_name = config.get("model", "zipformer")
                    logger.info(f"Client requested model: {model_name}")
                    # Allow client to override moderation setting
                    if "moderation" in config:
                        moderation_enabled = config.get("moderation", True)
            except json.JSONDecodeError:
                pass
        
        # Start model process
        manager.start_model(model_name)
        input_q, output_q = manager.get_queues(model_name)
        
        if not input_q or not output_q:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Failed to start model")
            return

        # Start detector if moderation is enabled
        if moderation_enabled:
            try:
                manager.start_detector("visobert-hsd")
                detector_input_q, detector_output_q = manager.get_detector_queues()
                if detector_input_q and detector_output_q:
                    logger.info("Content moderation enabled with visobert-hsd")
                else:
                    logger.warning("Failed to get detector queues, moderation disabled")
                    moderation_enabled = False
            except Exception as e:
                logger.warning(f"Failed to start detector: {e}, moderation disabled")
                moderation_enabled = False

        # If first message was audio, put it in queue
        if "bytes" in first_msg:
            await asyncio.to_thread(input_q.put, first_msg["bytes"])

        async def receive_audio():
            nonlocal session_id, model_name, input_q, output_q, moderation_enabled
            try:
                audio_packet_count = 0
                while True:
                    message = await websocket.receive()
                    
                    if message.get("type") == "websocket.disconnect":
                        logger.info("Client disconnected (receive loop)")
                        break
                        
                    if "bytes" in message:
                        audio_data = message["bytes"]
                        audio_packet_count += 1
                        if audio_packet_count % 50 == 0:
                            logger.debug(f"Received audio packet #{audio_packet_count}, size: {len(audio_data)} bytes")
                        # Use asyncio.to_thread to avoid blocking event loop
                        await asyncio.to_thread(input_q.put, audio_data)
                        
                    elif "text" in message:
                        try:
                            data = json.loads(message["text"])
                            msg_type = data.get("type")
                            
                            if msg_type == "config":
                                new_model = data.get("model")
                                if new_model and new_model != model_name:
                                    logger.info(f"Switching model to {new_model}")
                                    model_name = new_model
                                    manager.start_model(model_name)
                                    input_q, output_q = manager.get_queues(model_name)
                                # Allow toggling moderation mid-session
                                if "moderation" in data:
                                    moderation_enabled = data.get("moderation", True)
                                    manager.set_moderation_enabled(moderation_enabled)
                                    logger.info(f"Moderation toggled to: {moderation_enabled}")
                                    
                            elif msg_type == "start_session":
                                new_session_id = data.get("sessionId")
                                if new_session_id:
                                    session_id = new_session_id
                                    logger.info(f"Starting new session: {session_id}")
                                    await asyncio.to_thread(input_q.put, {"reset": True})
                                    
                            elif msg_type == "flush":
                                # Signal worker to force transcribe remaining buffer
                                logger.info("Received flush signal - forcing transcription of remaining buffer")
                                await asyncio.to_thread(input_q.put, {"flush": True})
                                    
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON message: {e}")
                            
            except WebSocketDisconnect:
                logger.info("Client disconnected (receive)")
            except RuntimeError as e:
                if "disconnect message has been received" not in str(e):
                    logger.error(f"RuntimeError receiving audio: {e}")
            except Exception as e:
                logger.error(f"Error receiving audio: {e}", exc_info=True)
            finally:
                # Signal that receive has ended - send_results should wait for pending results
                # DON'T set ws_closed here - let send_results drain the queue first
                receive_ended.set()
                logger.info("Receive ended, send_results will drain remaining queue")

        # Flag to signal when receive_audio has ended
        receive_ended = asyncio.Event()
        
        # Track WebSocket connection state
        ws_closed = asyncio.Event()
        
        async def send_results():
            nonlocal detector_input_q, moderation_enabled
            try:
                result_count = 0
                # Keep running until receive ended AND queue is empty for a while
                empty_checks = 0
                max_empty_checks = 200  # 200 * 50ms = 10s max wait after receive ends
                
                while True:
                    # Use asyncio.to_thread for blocking Queue operations
                    try:
                        # Check if queue has items (non-blocking)
                        is_empty = await asyncio.to_thread(lambda: output_q.empty())
                        if not is_empty:
                            result = await asyncio.to_thread(output_q.get_nowait)
                            result_count += 1
                            empty_checks = 0  # Reset counter when we get data
                            
                            # Check WebSocket state before sending (only set on send error)
                            if ws_closed.is_set():
                                logger.debug("WebSocket already closed, discarding result")
                                continue  # Continue to drain queue for DB save
                                
                            try:
                                await websocket.send_json(result)
                                logger.info(f"Sent result #{result_count} to client: '{result.get('text', '')[:50]}...'")
                            except Exception as send_err:
                                logger.warning(f"Failed to send result (client disconnected): {send_err}")
                                ws_closed.set()  # Mark WebSocket as closed on send error
                            
                            # Content moderation: send text to detector if is_final and moderation enabled
                            is_final = result.get("is_final", False)
                            text_content = result.get("text", "").strip()
                            
                            if (is_final and text_content and moderation_enabled 
                                and detector_input_q is not None
                                and (not settings.MODERATION_ON_FINAL_ONLY or is_final)):
                                # Send text to detector with unique request_id
                                request_id = str(uuid.uuid4())[:8]
                                detector_request = {
                                    "request_id": request_id,
                                    "text": text_content,
                                    "session_id": session_id
                                }
                                try:
                                    await asyncio.to_thread(detector_input_q.put_nowait, detector_request)
                                    logger.debug(f"Sent text to detector: '{text_content[:30]}...'")
                                except Exception as e:
                                    logger.warning(f"Failed to send to detector: {e}")
                            
                            # Save to DB only if we have a session ID from client
                            latency_ms = result.get("latency_ms", 0.0)
                            workflow_type = result.get("workflow_type", "streaming")  # Default to streaming for zipformer
                            if text_content and session_id:
                                await _save_transcription(
                                    session_id=session_id,
                                    model_id=model_name,
                                    content=text_content,
                                    latency_ms=latency_ms,
                                    workflow_type=workflow_type
                                )
                        else:
                            # Queue is empty
                            if receive_ended.is_set():
                                empty_checks += 1
                                if empty_checks >= max_empty_checks:
                                    logger.info(f"Receive ended and queue empty for {empty_checks * 50}ms, closing send_results")
                                    break
                            await asyncio.sleep(0.05)  # 50ms polling interval
                            
                    except Exception as e:
                        if "Empty" not in str(type(e).__name__):
                            logger.error(f"Error in send_results: {e}")
                        await asyncio.sleep(0.05)
                        
            except Exception as e:
                logger.error(f"Error sending results: {e}", exc_info=True)

        async def send_moderation_results():
            """Send content moderation results from detector to client."""
            nonlocal detector_output_q, moderation_enabled
            if not moderation_enabled or detector_output_q is None:
                return
                
            try:
                while True:
                    # Wait until receive is done or ws is closed
                    if receive_ended.is_set() and ws_closed.is_set():
                        break
                        
                    try:
                        is_empty = await asyncio.to_thread(lambda: detector_output_q.empty())
                        if not is_empty:
                            moderation_result = await asyncio.to_thread(detector_output_q.get_nowait)
                            
                            if ws_closed.is_set():
                                logger.debug("WebSocket closed, discarding moderation result")
                                continue
                            
                            # Format moderation result for client
                            client_result = {
                                "type": "moderation",
                                "request_id": moderation_result.get("request_id"),
                                "label": moderation_result.get("label"),
                                "label_id": moderation_result.get("label_id"),
                                "confidence": moderation_result.get("confidence"),
                                "is_flagged": moderation_result.get("is_flagged", False),
                                "latency_ms": moderation_result.get("latency_ms", 0)
                            }
                            
                            try:
                                await websocket.send_json(client_result)
                                logger.info(f"Sent moderation result: {client_result['label']} ({client_result['confidence']:.2%})")
                            except Exception as send_err:
                                logger.warning(f"Failed to send moderation result: {send_err}")
                                ws_closed.set()
                        else:
                            await asyncio.sleep(0.05)
                            
                        # Exit if receive ended and no more results expected
                        if receive_ended.is_set():
                            # Give extra time for pending moderation results
                            await asyncio.sleep(0.5)
                            is_still_empty = await asyncio.to_thread(lambda: detector_output_q.empty())
                            if is_still_empty:
                                break
                                
                    except Exception as e:
                        if "Empty" not in str(type(e).__name__):
                            logger.error(f"Error in send_moderation_results: {e}")
                        await asyncio.sleep(0.05)
                        
            except Exception as e:
                logger.error(f"Error in moderation results loop: {e}", exc_info=True)

        # Run tasks concurrently
        receive_task = asyncio.create_task(receive_audio())
        send_task = asyncio.create_task(send_results())
        moderation_task = asyncio.create_task(send_moderation_results()) if moderation_enabled else None
        
        # Wait for receive to finish first (client disconnect or error)
        await receive_task
        
        # Now wait for send_results to drain the queue (with timeout)
        try:
            # Give send_results up to 15 seconds to drain remaining results
            await asyncio.wait_for(send_task, timeout=15.0)
            logger.info("send_results completed successfully")
        except asyncio.TimeoutError:
            logger.warning("send_results timed out after 15s, cancelling")
            send_task.cancel()
            try:
                await send_task
            except asyncio.CancelledError:
                pass
        
        # Wait for moderation task if enabled
        if moderation_task:
            try:
                await asyncio.wait_for(moderation_task, timeout=5.0)
                logger.info("moderation task completed successfully")
            except asyncio.TimeoutError:
                logger.warning("moderation task timed out, cancelling")
                moderation_task.cancel()
                try:
                    await moderation_task
                except asyncio.CancelledError:
                    pass
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)


async def _save_transcription(
    session_id: str, 
    model_id: str, 
    content: str, 
    latency_ms: float = 0.0,
    workflow_type: str = "streaming"
):
    """Save transcription to database with fresh session.
    
    For streaming workflow (Zipformer): REPLACE content (each result contains full transcription)
    """
    from sqlalchemy.orm import sessionmaker
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            # Check if log exists for this session
            statement = select(TranscriptionLog).where(TranscriptionLog.session_id == session_id)
            existing_log = (await session.exec(statement)).first()
            
            if existing_log:
                if workflow_type == "streaming":
                    # REPLACE: Streaming models send cumulative text
                    existing_log.content = content
                    logger.debug(f"Replaced transcription for session {session_id}: '{content[:30]}...'")
                else:
                    # APPEND: Buffered models send separate chunks
                    if existing_log.content and content:
                        existing_log.content = f"{existing_log.content} {content}"
                    elif content:
                        existing_log.content = content
                    logger.debug(f"Appended transcription to session {session_id}: '{content[:30]}...'")
                    
                # Keep max latency for the session
                if latency_ms > existing_log.latency_ms:
                    existing_log.latency_ms = latency_ms
                session.add(existing_log)
            else:
                db_log = TranscriptionLog(
                    session_id=session_id,
                    model_id=model_id,
                    content=content,
                    latency_ms=latency_ms,
                )
                session.add(db_log)
                logger.debug(f"Created new transcription for session {session_id}")
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to save transcription: {e}")
            await session.rollback()

@router.post("/api/v1/models/switch", 
             response_model=SwitchModelResponse,
             summary="Switch active model",
             responses={
                 400: {"description": "Invalid model name", "content": {"application/problem+json": {}}},
                 503: {"description": "Model failed to start", "content": {"application/problem+json": {}}}
             })
def switch_model(model: str):
    """
    Manually switch the active model.
    
    Available models: zipformer
    """
    valid_models = ["zipformer"]
    if model not in valid_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid model. Valid options: {valid_models}"
        )
    try:
        manager.start_model(model)
        return SwitchModelResponse(status="success", current_model=model)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Failed to start model: {str(e)}")


@router.get("/api/v1/models/status", response_model=ModelStatus, summary="Get model status")
async def get_model_status():
    """Get the status of the currently loaded model."""
    current_model = manager.current_model
    loading_model = manager.loading_model
    status = manager.get_status()
    
    return ModelStatus(
        current_model=loading_model if status == "loading" else current_model,
        is_loaded=status == "ready",
        status=status
    )


@router.get("/api/v1/moderation/status", summary="Get content moderation status")
async def get_moderation_status():
    """Get the current status of content moderation."""
    return {
        "enabled": manager.moderation_enabled,
        "current_detector": manager.current_detector,
        "loading_detector": manager.loading_detector,
        "config": {
            "default_enabled": settings.ENABLE_CONTENT_MODERATION,
            "confidence_threshold": settings.MODERATION_CONFIDENCE_THRESHOLD,
            "on_final_only": settings.MODERATION_ON_FINAL_ONLY
        }
    }


@router.post("/api/v1/moderation/toggle", summary="Toggle content moderation")
async def toggle_moderation(enabled: bool = True):
    """
    Enable or disable content moderation.
    
    - When enabled: Starts the detector if not running, enables moderation
    - When disabled: Keeps detector running but stops sending moderation results
    """
    if enabled:
        if not manager.current_detector:
            try:
                manager.start_detector("visobert-hsd")
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to start detector: {str(e)}"
                )
        manager.set_moderation_enabled(True)
    else:
        manager.set_moderation_enabled(False)
    
    return {
        "enabled": manager.moderation_enabled,
        "current_detector": manager.current_detector
    }
