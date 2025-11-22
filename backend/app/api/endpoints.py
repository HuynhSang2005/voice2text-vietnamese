from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Any
import asyncio
import json
import queue
from app.core.manager import manager
from app.models.schema import Transcription
from app.api.deps import get_session
from sqlmodel import Session

router = APIRouter()

@router.websocket("/ws/transcribe")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    model_name = "zipformer" # Default
    
    try:
        # 1. Wait for config message
        data = await websocket.receive_text()
        config = json.loads(data)
        if config.get("type") == "config":
            model_name = config.get("model", "zipformer")
            print(f"Client requested model: {model_name}")
            
        # Start model process
        manager.start_model(model_name)
        input_q, output_q = manager.get_queues(model_name)
        
        if not input_q or not output_q:
            await websocket.close(code=1000, reason="Failed to start model")
            return

        async def receive_audio():
            try:
                while True:
                    data = await websocket.receive_bytes()
                    # Send to worker
                    input_q.put(data)
            except WebSocketDisconnect:
                print("Client disconnected")
                # manager.stop_current_model() # Optional: stop if single user
            except Exception as e:
                print(f"Error receiving audio: {e}")

        async def send_results():
            try:
                while True:
                    # Non-blocking check of output queue
                    try:
                        # We need to poll because queue.get is blocking and not async
                        # Use run_in_executor to wait for queue? 
                        # Or just poll with sleep. Polling is safer for simple implementation.
                        while not output_q.empty():
                            result = output_q.get_nowait()
                            await websocket.send_json(result)
                        
                        await asyncio.sleep(0.05) # 50ms poll interval
                    except queue.Empty:
                        await asyncio.sleep(0.05)
            except Exception as e:
                print(f"Error sending results: {e}")

        # Run both tasks
        await asyncio.gather(receive_audio(), send_results())

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Cleanup if needed
        pass

@router.post("/models/switch")
def switch_model(model: str):
    """
    Manually switch model via REST (optional, mostly for testing).
    """
    try:
        manager.start_model(model)
        return {"status": "success", "current_model": model}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history", response_model=list[Transcription])
def get_history(session: Session = Depends(get_session)):
    # Placeholder for history retrieval
    # In a real app, we would query the DB
    return []
