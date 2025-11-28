# SYSTEM SPECIFICATION: BACKEND (FastAPI + Real-time AI)

## 1. TECH STACK & DEPENDENCIES

The Agent MUST generate code using the following libraries (versions are indicative):

- python >= 3.10
- fastapi, uvicorn[standard], websockets
- sqlmodel (for ORM), aiosqlite
- torch (CPU version is fine for dev)
- sherpa-onnx (For Zipformer streaming)
- faster-whisper (For Whisper/PhoWhisper)
- silero-vad (For Voice Activity Detection)
- numpy, librosa

## 2. PROJECT STRUCTURE & RESPONSIBILITIES

### A. Entry Point (`app/main.py`)

- Initialize FastAPI app.
- Configure CORS (Allow all origins for dev).
- Include routers from `app.api.endpoints`.
- **Constraint:** Must use `lifespan` event to initialize the `ModelManager` and Database creation.

### B. The Model Manager (`app/core/manager.py`)

- **Role:** Singleton class acting as the orchestrator.
- **Attributes:**
  - `active_process`: Holds the current `multiprocessing.Process`.
  - `input_queue`: `multiprocessing.Queue` (Sender).
  - `output_queue`: `multiprocessing.Queue` (Receiver).
- **Methods:**
  - `switch_model(model_id: str)`:
    1. Terminate current process if alive.
    2. Create new Queue pair.
    3. Spawn new Process based on model_id (ZipformerWorker or WhisperWorker).
    4. Start process.

### C. Worker Interface (`app/workers/base.py`)

- Must define an Abstract Base Class `BaseWorker`.
- **Method Signature:** `run(input_queue: Queue, output_queue: Queue, model_path: str)`
- **Constraint:** All model imports (e.g., `import sherpa_onnx`) MUST happen INSIDE the `run` method to avoid Pickling errors in Multiprocessing.

### D. Worker Implementations

1. **`ZipformerWorker` (`app/workers/zipformer.py`):**

   - Initialize `sherpa_onnx.OnlineRecognizer`.
   - Loop: Read audio chunk -> `stream.accept_waveform()` -> `recognizer.decode_stream()` -> Check result.
   - If text detected -> Put `{ "text": ..., "is_final": False }` to output_queue.

2. **`WhisperWorker` (`app/workers/whisper.py`):**
   - Initialize `faster_whisper.WhisperModel` (int8).
   - Logic: Accumulate chunks into a buffer.
   - Use `silero_vad` to detect speech end.
   - If silence > 500ms OR buffer > 3s: Run `model.transcribe()` -> Put `{ "text": ..., "is_final": True }`.

## 3. WEBSOCKET PROTOCOL (`app/api/endpoints.py`)

**Endpoint:** `@router.websocket("/ws/transcribe")`

**Logic Flow (Pseudo-code):**

```python
await websocket.accept()
try:
    while True:
        # 1. Non-blocking receive
        try:
            data = await asyncio.wait_for(websocket.receive(), timeout=0.01)
            if isinstance(data, dict): # Config JSON
                 manager.switch_model(data['model_id'])
            elif isinstance(data, bytes): # Audio PCM
                 manager.input_queue.put(data)
        except TimeoutError:
            pass # Just continue to check output queue

        # 2. Check Output Queue (Non-blocking)
        while not manager.output_queue.empty():
            result = manager.output_queue.get_nowait()
            await websocket.send_json(result)

            # 3. Async Save to DB (Fire and Forget logic)
            if result['is_final']:
                save_transcription_to_db(result)
except Disconnect:
    manager.cleanup()
```

## 4\. DATABASE SCHEMA (`app/models/schema.py`)

Use SQLModel.

```python
class TranscriptionLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str
    model_id: str
    content: str
    latency_ms: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

## 5\. CRITICAL PERFORMANCE RULES

1.  **Queues:** Use `multiprocessing.Queue`, NOT `queue.Queue`.
2.  **Audio Format:** Backend expects **Raw PCM Int16 16000Hz**. Workers must convert bytes to `numpy.float32` normalized [-1, 1] if the specific model requires it (Sherpa handles this, Whisper needs float32).
3.  **Process Safety:** Ensure `if __name__ == "__main__":` block exists in `main.py` to support Windows/MacOS multiprocessing spawn methods.

## 6. API SECURITY & SPECIFICATION (New)

### A. CORS Configuration (`app/main.py`)

The Agent MUST configure CORS to allow the Frontend to communicate.

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### B. OpenAPI Customization

The Agent MUST customize the OpenAPI schema so the generated client knows the Base URL.

```python
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Real-time STT API",
        version="1.0.0",
        routes=app.routes,
    )
    # CRITICAL: Hardcode local server for generated client to work out-of-the-box
    openapi_schema["servers"] = [{"url": "http://localhost:8000"}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### C. Endpoint Definition (`app/api/endpoints.py`)

The Agent MUST use strict Pydantic models for Responses so Swagger UI is accurate.

- `GET /api/v1/models` -\> Response Model: `List[ModelInfo]`
- `GET /api/v1/history` -\> Response Model: `List[TranscriptionLog]`

```

```
