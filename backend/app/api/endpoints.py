import asyncio
import json
import queue
from typing import List, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.core.manager import manager
from app.models.schema import TranscriptionLog
from app.api.deps import get_session
from app.models.protocols import ModelInfo

router = APIRouter()

@router.get("/api/v1/models", response_model=List[ModelInfo])
async def get_models():
    """List available speech-to-text models."""
    return [
        ModelInfo(id="zipformer", name="Zipformer (Offline)", description="High accuracy, offline processing"),
        ModelInfo(id="faster-whisper", name="Faster Whisper (Buffered)", description="High accuracy, buffered processing"),
        ModelInfo(id="phowhisper", name="PhoWhisper (Buffered)", description="Vietnamese optimized Whisper"),
        ModelInfo(id="hkab", name="HKAB (Streaming)", description="Experimental Streaming RNN-T"),
    ]

@router.get("/api/v1/history", response_model=List[TranscriptionLog])
async def get_history(session: AsyncSession = Depends(get_session)):
    """Get transcription history."""
    result = await session.exec(select(TranscriptionLog).order_by(TranscriptionLog.created_at.desc()).limit(50))
    return result.all()

@router.websocket("/ws/transcribe")
async def websocket_endpoint(websocket: WebSocket, session: AsyncSession = Depends(get_session)):
    await websocket.accept()
    
    model_name = "zipformer" # Default
    # Initial session ID (connection-based)
    session_id = str(id(websocket)) 
    
    try:
        # 1. Wait for config message (Optional, or first message)
        first_msg = await websocket.receive()
        
        if "text" in first_msg:
            try:
                config = json.loads(first_msg["text"])
                if config.get("type") == "config":
                    model_name = config.get("model", "zipformer")
                    print(f"Client requested model: {model_name}")
            except json.JSONDecodeError:
                pass
        elif "bytes" in first_msg:
            # It's audio, put it in queue later
            pass
            
        # Start model process
        manager.start_model(model_name)
        input_q, output_q = manager.get_queues(model_name)
        
        if not input_q or not output_q:
            await websocket.close(code=1000, reason="Failed to start model")
            return

        # If first message was audio, put it in queue
        if "bytes" in first_msg:
             input_q.put(first_msg["bytes"])

        async def receive_audio():
            nonlocal session_id, model_name, input_q, output_q # Allow updating from inner scope
            try:
                audio_packet_count = 0
                while True:
                    message = await websocket.receive()
                    
                    if message["type"] == "websocket.disconnect":
                        print("Client disconnected (receive loop)")
                        break
                        
                    if "bytes" in message:
                        audio_data = message["bytes"]
                        audio_packet_count += 1
                        if audio_packet_count % 10 == 0:
                            print(f"[WebSocket] Received audio packet #{audio_packet_count}, size: {len(audio_data)} bytes")
                        input_q.put(audio_data)
                    elif "text" in message:
                        try:
                            data = json.loads(message["text"])
                            msg_type = data.get("type")
                            
                            if msg_type == "config":
                                new_model = data.get("model")
                                if new_model and new_model != model_name:
                                    print(f"Switching model to {new_model}")
                                    model_name = new_model
                                    
                                    # Switch model in manager
                                    manager.start_model(model_name)
                                    input_q, output_q = manager.get_queues(model_name)
                                    
                            elif msg_type == "start_session":
                                # Client starting a new recording session
                                new_session_id = data.get("sessionId")
                                if new_session_id:
                                    session_id = new_session_id
                                    print(f"[WebSocket] Starting new session: {session_id}")
                                    
                                    # Signal worker to reset context
                                    input_q.put({"reset": True})
                                    
                        except Exception as e:
                            print(f"Error parsing text message: {e}")
                            pass
            except WebSocketDisconnect:
                print("Client disconnected (receive)")
            except RuntimeError as e:
                if "disconnect message has been received" in str(e):
                    print("Client disconnected (RuntimeError)")
                else:
                    print(f"RuntimeError receiving audio: {e}")
            except Exception as e:
                print(f"Error receiving audio: {e}")
                import traceback
                traceback.print_exc()

        async def send_results():
            try:
                result_count = 0
                while True:
                    # Non-blocking check
                    try:
                        while not output_q.empty():
                            result = output_q.get_nowait()
                            result_count += 1
                            
                            # print(f"[WebSocket] Sending result #{result_count}: text='{result.get('text', '')}', is_final={result.get('is_final')}")
                            
                            # Send to client
                            await websocket.send_json(result)
                            
                            # Save to DB if final OR if we want to save partials? 
                            # Usually we save final. 
                            # But since we are using OfflineRecognizer in buffered mode, we might want to save 
                            # the "final" result of the session when the session ends?
                            # OR, we can just save whatever we have as a log entry.
                            # For now, let's save if text is not empty (updates the log)
                            
                            text_content = result.get("text", "").strip()
                            if text_content:
                                # We want to UPSERT or INSERT?
                                # If we want one log per session, we should update the existing entry for this session_id?
                                # OR just insert a new log for every update? Inserting every update is too much.
                                # Let's insert only if it's "final" (which we don't have yet from worker)
                                # OR, let's assume the client will send a "stop_session" to mark finality?
                                # For simplicity requested by user: "mỗi lần mở mic... là 1 session"
                                # We can log the latest text for this session_id.
                                
                                # Check if log exists for this session
                                statement = select(TranscriptionLog).where(TranscriptionLog.session_id == session_id)
                                existing_log = (await session.exec(statement)).first()
                                
                                if existing_log:
                                    existing_log.content = text_content
                                    session.add(existing_log)
                                else:
                                    db_log = TranscriptionLog(
                                        session_id=session_id,
                                        model_id=model_name,
                                        content=text_content,
                                        latency_ms=0.0,
                                    )
                                    session.add(db_log)
                                await session.commit()
                                
                        # Optimize: Yield control to event loop to prevent starvation
                        await asyncio.sleep(0.01) 
                    except queue.Empty:
                        await asyncio.sleep(0.01)
            except Exception as e:
                print(f"Error sending results: {e}")

        # Run both tasks
        # Use asyncio.wait to handle task cancellation properly
        tasks = [
            asyncio.create_task(receive_audio()),
            asyncio.create_task(send_results())
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Optional: Stop model if it's a dedicated session
        # manager.stop_current_model()
        pass

@router.post("/models/switch", 
             responses={
                 400: {"description": "Invalid model name", "content": {"application/problem+json": {}}},
                 503: {"description": "Model failed to start", "content": {"application/problem+json": {}}}
             })
def switch_model(model: str):
    """
    Manually switch model via REST (optional, mostly for testing).
    """
    try:
        manager.start_model(model)
        return {"status": "success", "current_model": model}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to start model: {str(e)}")
