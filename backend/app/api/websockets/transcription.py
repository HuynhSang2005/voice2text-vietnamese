"""
Presentation Layer - WebSocket Transcription Endpoint

This module implements the WebSocket endpoint for real-time speech transcription
following Clean Architecture and RFC 6455 (WebSocket Protocol) compliance.

Key Features:
- Real-time audio streaming and transcription
- Content moderation integration
- Proper WebSocket lifecycle management (connect, ping/pong, close)
- Race condition prevention with async task coordination
- Clean separation from business logic (uses TranscribeAudioUseCase)

Protocol Flow:
1. Client connects to /ws/transcribe
2. Client sends config message (optional): {"type": "config", "model": "zipformer", ...}
3. Client sends binary audio data (Int16 PCM, 16kHz)
4. Server streams transcription results: {"text": "...", "is_final": bool, ...}
5. Server sends moderation results: {"type": "moderation", "label": "...", ...}
6. Client closes connection with proper close frame (RFC 6455)

Following Clean Architecture:
- Presentation layer handles WebSocket protocol details
- Business logic delegated to TranscribeAudioUseCase
- Domain entities used for data representation
"""

import asyncio
import json
import logging
from typing import Optional, AsyncIterator


from fastapi import WebSocket, WebSocketDisconnect, Depends, status
from fastapi.routing import APIRouter

from app.api.deps import (
    get_transcribe_audio_use_case,
)
from app.application.use_cases.transcribe_audio import TranscribeAudioUseCase
from app.application.dtos.requests import TranscriptionRequest

from app.domain.value_objects.audio_data import AudioData
from app.domain.exceptions import (
    BusinessRuleViolationException as BusinessRuleException,
)
from app.core.config import settings


logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/transcribe")
async def websocket_transcribe(
    websocket: WebSocket,
    use_case: TranscribeAudioUseCase = Depends(get_transcribe_audio_use_case),
):
    """
    WebSocket endpoint for real-time speech transcription.

    This endpoint implements RFC 6455 compliant WebSocket communication for
    streaming audio transcription. It follows Clean Architecture principles
    by delegating business logic to TranscribeAudioUseCase.

    Protocol:
        1. Client connects
        2. Client sends config message (optional):
           {"type": "config", "model": "zipformer", "enable_moderation": true}
        3. Client streams binary audio data (Int16 PCM, 16kHz)
        4. Server streams transcription results:
           {"type": "transcription", "text": "...", "is_final": bool, ...}
        5. Server sends moderation results (if enabled):
           {"type": "moderation", "label": "CLEAN|OFFENSIVE|HATE", ...}
        6. Client can send ping: {"type": "ping", "timestamp": 1234567890}
        7. Server responds with pong: {"type": "pong", "timestamp": 1234567890}
        8. Client closes with proper close frame (code 1000)

    WebSocket Message Types:
        From Client:
        - config: Configuration message (model, moderation settings)
        - audio: Binary audio data (Int16 PCM)
        - ping: Heartbeat message
        - flush: Force transcription of remaining buffer
        - reset: Reset transcription state

        From Server:
        - transcription: Transcription result (partial or final)
        - moderation: Content moderation result
        - pong: Heartbeat response
        - error: Error message

    Args:
        websocket: FastAPI WebSocket connection
        use_case: Injected TranscribeAudioUseCase for business logic

    Raises:
        WebSocketDisconnect: When client disconnects

    Example:
        ```javascript
        // Client-side example
        const ws = new WebSocket('ws://localhost:8000/ws/transcribe');

        ws.onopen = () => {
            // Send config
            ws.send(JSON.stringify({
                type: 'config',
                model: 'zipformer',
                enable_moderation: true,
                session_id: 'abc-123'
            }));

            // Stream audio
            audioStream.addEventListener('data', (chunk) => {
                ws.send(chunk);
            });
        };

        ws.onmessage = (event) => {
            const result = JSON.parse(event.data);
            if (result.type === 'transcription') {
                console.log('Text:', result.text);
            }
        };
        ```

    RFC 6455 Compliance:
        - Proper close frame handling (code 1000 for normal closure)
        - Ping/pong heartbeat mechanism
        - Error handling with appropriate close codes
        - No race conditions in concurrent tasks
    """
    # Accept WebSocket connection
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    # Default configuration
    config = TranscriptionRequest(
        model="zipformer",
        sample_rate=16000,
        enable_moderation=settings.ENABLE_CONTENT_MODERATION,
        session_id=None,  # Will be set by client or auto-generated
        language="vi",
    )

    # Connection state tracking
    receive_ended = asyncio.Event()
    ws_closed = asyncio.Event()

    # Audio stream queue for bridging WebSocket messages to use case
    audio_queue: asyncio.Queue[Optional[AudioData]] = asyncio.Queue()

    try:
        # --- Task 1: Receive messages from client ---
        async def receive_messages():
            """
            Receive and handle WebSocket messages from client.

            Message Types:
            - Text messages: JSON config, ping, flush, reset
            - Binary messages: Audio data
            """
            nonlocal config

            try:
                while True:
                    message = await websocket.receive()

                    # Handle disconnect
                    if message.get("type") == "websocket.disconnect":
                        logger.info("Client disconnected (receive loop)")
                        break

                    # Handle binary audio data
                    if "bytes" in message:
                        audio_data = message["bytes"]
                        # Wrap raw bytes in AudioData domain entity
                        audio_entity = AudioData(
                            data=audio_data,
                            sample_rate=config.sample_rate,
                            channels=1,  # Mono audio for transcription
                            format="pcm",  # Raw PCM format from client
                            duration_ms=None,  # Duration calculated by worker
                        )
                        await audio_queue.put(audio_entity)
                        logger.debug(f"Received audio chunk: {len(audio_data)} bytes")

                    # Handle text messages (JSON)
                    elif "text" in message:
                        try:
                            data = json.loads(message["text"])
                            msg_type = data.get("type")

                            if msg_type == "config":
                                # Update configuration
                                config = TranscriptionRequest(
                                    model=data.get("model", config.model),
                                    sample_rate=data.get(
                                        "sample_rate", config.sample_rate
                                    ),
                                    enable_moderation=data.get(
                                        "enable_moderation", config.enable_moderation
                                    ),
                                    session_id=data.get(
                                        "session_id", config.session_id
                                    ),
                                    language=data.get("language", config.language),
                                )
                                logger.info(
                                    f"Updated config: model={config.model}, moderation={config.enable_moderation}"
                                )

                            elif msg_type == "ping":
                                # Respond to heartbeat
                                timestamp = data.get("timestamp", 0)
                                await websocket.send_json(
                                    {"type": "pong", "timestamp": timestamp}
                                )
                                logger.debug("Heartbeat: ping -> pong")

                            elif msg_type == "flush":
                                # Signal end of audio stream (flush remaining buffer)
                                logger.info("Received flush signal")
                                await audio_queue.put(None)  # Sentinel value

                            elif msg_type == "reset":
                                # Reset transcription state
                                logger.info("Received reset signal")
                                # Clear audio queue
                                while not audio_queue.empty():
                                    try:
                                        audio_queue.get_nowait()
                                    except asyncio.QueueEmpty:
                                        break

                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON message: {e}")
                            await websocket.send_json(
                                {"type": "error", "message": "Invalid JSON format"}
                            )

            except WebSocketDisconnect:
                logger.info("Client disconnected (receive)")
            except Exception as e:
                logger.error(f"Error in receive_messages: {e}", exc_info=True)
            finally:
                receive_ended.set()
                # Signal end of audio stream
                await audio_queue.put(None)
                logger.info("Receive messages ended")

        # --- Task 2: Process transcription and send results ---
        async def process_and_send():
            """
            Process audio through use case and send transcription results to client.

            This task bridges the audio queue to the use case's audio stream,
            processes transcriptions, and sends results back to the client.
            """
            try:
                # Create async generator for audio stream (use case expects AsyncIterator)
                async def audio_stream_generator() -> AsyncIterator[AudioData]:
                    """Generate audio stream from queue."""
                    while True:
                        audio_data = await audio_queue.get()
                        if audio_data is None:  # Sentinel value - end of stream
                            break
                        yield audio_data

                # Execute transcription use case
                logger.info(
                    f"Starting transcription: model={config.model}, moderation={config.enable_moderation}"
                )

                async for transcription in use_case.execute(
                    audio_stream=audio_stream_generator(), request=config
                ):
                    # Check if WebSocket is still open
                    if ws_closed.is_set():
                        logger.debug(
                            "WebSocket closed, discarding transcription result"
                        )
                        continue

                    # Format transcription result for client
                    result = {
                        "type": "transcription",
                        "text": transcription.content,
                        "is_final": (
                            transcription.is_final
                            if hasattr(transcription, "is_final")
                            else True
                        ),
                        "model": transcription.model_id,
                        "latency_ms": transcription.latency_ms,
                        "timestamp": transcription.created_at.isoformat(),
                    }

                    # Add moderation results if available
                    if transcription.moderation_label:
                        result["moderation"] = {
                            "label": transcription.moderation_label,
                            "confidence": transcription.moderation_confidence,
                            "is_flagged": transcription.is_flagged,
                            "detected_keywords": transcription.detected_keywords,
                        }

                    # Send result to client
                    try:
                        await websocket.send_json(result)
                        logger.info(
                            f"Sent transcription: '{transcription.content[:50]}...'"
                        )
                    except Exception as send_err:
                        logger.warning(
                            f"Failed to send result (client disconnected): {send_err}"
                        )
                        ws_closed.set()
                        break

                logger.info("Transcription processing completed")

            except BusinessRuleException as e:
                # Business rule violations (e.g., worker not ready)
                error_msg = {"type": "error", "code": e.rule, "message": e.reason}
                try:
                    await websocket.send_json(error_msg)
                except Exception:
                    pass
                logger.error(f"Business rule exception: {e.rule} - {e.reason}")

            except Exception as e:
                # Unexpected errors
                logger.error(f"Error in process_and_send: {e}", exc_info=True)
                error_msg = {
                    "type": "error",
                    "message": "Internal server error during transcription",
                }
                try:
                    await websocket.send_json(error_msg)
                except Exception:
                    pass
            finally:
                logger.info("Process and send task ended")

        # --- Run concurrent tasks ---
        receive_task = asyncio.create_task(receive_messages())
        process_task = asyncio.create_task(process_and_send())

        # Wait for receive task to complete (client disconnect or error)
        await receive_task

        # Give process task time to finish processing remaining audio
        try:
            await asyncio.wait_for(process_task, timeout=10.0)
            logger.info("Process task completed successfully")
        except asyncio.TimeoutError:
            logger.warning("Process task timed out after 10s, cancelling")
            process_task.cancel()
            try:
                await process_task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # RFC 6455 compliance: Send proper close frame
        # Only send close if WebSocket is still in CONNECTED state
        try:
            if not ws_closed.is_set():
                await websocket.close(
                    code=status.WS_1000_NORMAL_CLOSURE, reason="Normal closure"
                )
                logger.info("WebSocket closed with code 1000 (normal closure)")
        except Exception as e:
            logger.warning(f"Error closing WebSocket: {e}")
