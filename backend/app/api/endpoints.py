import asyncio
import json
import logging
from typing import List, Any
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.core.manager import manager
from app.core.database import get_session, engine
from app.models.schema import TranscriptionLog
from app.models.protocols import ModelInfo, ModelStatus, SwitchModelResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Speech-to-Text"])

@router.get("/api/v1/models", response_model=List[ModelInfo], summary="List available models")
async def get_models():
    """List available speech-to-text models with their capabilities."""
    return [
        ModelInfo(id="zipformer", name="Zipformer (Offline)", description="High accuracy, offline processing"),
        ModelInfo(id="faster-whisper", name="Faster Whisper (Buffered)", description="High accuracy, buffered processing"),
        ModelInfo(id="phowhisper", name="PhoWhisper (Buffered)", description="Vietnamese optimized Whisper"),
        ModelInfo(id="hkab", name="HKAB (Streaming)", description="Experimental Streaming RNN-T"),
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
    """
    await websocket.accept()
    
    model_name = "zipformer"  # Default
    session_id = str(id(websocket))
    
    try:
        # 1. Wait for config message (Optional, or first message)
        first_msg = await websocket.receive()
        
        if "text" in first_msg:
            try:
                config = json.loads(first_msg["text"])
                if config.get("type") == "config":
                    model_name = config.get("model", "zipformer")
                    logger.info(f"Client requested model: {model_name}")
            except json.JSONDecodeError:
                pass
        
        # Start model process
        manager.start_model(model_name)
        input_q, output_q = manager.get_queues(model_name)
        
        if not input_q or not output_q:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Failed to start model")
            return

        # If first message was audio, put it in queue
        if "bytes" in first_msg:
            await asyncio.to_thread(input_q.put, first_msg["bytes"])

        async def receive_audio():
            nonlocal session_id, model_name, input_q, output_q
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
                                    
                            elif msg_type == "start_session":
                                new_session_id = data.get("sessionId")
                                if new_session_id:
                                    session_id = new_session_id
                                    logger.info(f"Starting new session: {session_id}")
                                    await asyncio.to_thread(input_q.put, {"reset": True})
                                    
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON message: {e}")
                            
            except WebSocketDisconnect:
                logger.info("Client disconnected (receive)")
            except RuntimeError as e:
                if "disconnect message has been received" not in str(e):
                    logger.error(f"RuntimeError receiving audio: {e}")
            except Exception as e:
                logger.error(f"Error receiving audio: {e}", exc_info=True)

        async def send_results():
            try:
                result_count = 0
                while True:
                    # Use asyncio.to_thread for blocking Queue operations
                    try:
                        # Check if queue has items (non-blocking)
                        is_empty = await asyncio.to_thread(lambda: output_q.empty())
                        if not is_empty:
                            result = await asyncio.to_thread(output_q.get_nowait)
                            result_count += 1
                            
                            await websocket.send_json(result)
                            
                            # Save to DB with fresh session (avoid session expiry)
                            text_content = result.get("text", "").strip()
                            if text_content:
                                await _save_transcription(
                                    session_id=session_id,
                                    model_id=model_name,
                                    content=text_content
                                )
                        else:
                            await asyncio.sleep(0.02)  # 20ms polling interval
                            
                    except Exception as e:
                        if "Empty" not in str(type(e).__name__):
                            logger.error(f"Error in send_results: {e}")
                        await asyncio.sleep(0.02)
                        
            except Exception as e:
                logger.error(f"Error sending results: {e}", exc_info=True)

        # Run both tasks concurrently
        tasks = [
            asyncio.create_task(receive_audio()),
            asyncio.create_task(send_results())
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)


async def _save_transcription(session_id: str, model_id: str, content: str):
    """Save transcription to database with fresh session."""
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
                existing_log.content = content
                session.add(existing_log)
            else:
                db_log = TranscriptionLog(
                    session_id=session_id,
                    model_id=model_id,
                    content=content,
                    latency_ms=0.0,
                )
                session.add(db_log)
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
    
    Available models: zipformer, faster-whisper, phowhisper, hkab
    """
    valid_models = ["zipformer", "faster-whisper", "phowhisper", "hkab"]
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
    is_loaded = current_model is not None and current_model in manager.active_processes
    
    return ModelStatus(
        current_model=current_model,
        is_loaded=is_loaded,
        status="ready" if is_loaded else "idle"
    )
