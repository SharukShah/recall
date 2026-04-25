"""
Voice WebSocket router — bridges client audio to Deepgram Voice Agent API.
Endpoint: ws://localhost:8000/ws/voice
"""
import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import websockets
import websockets.exceptions

from config import settings
from services.voice_service import VoiceSessionManager, UnifiedVoiceSession

logger = logging.getLogger(__name__)
router = APIRouter()

DEEPGRAM_AGENT_URL = "wss://agent.deepgram.com/v1/agent/converse"


# Simple in-memory rate limiter for WS sessions
_rate_lock = asyncio.Lock()
_session_starts: dict[str, list[float]] = {}
_MAX_SESSIONS_PER_HOUR = 10
_active_sessions: dict[str, int] = {}  # ip → count of active sessions
_MAX_CONCURRENT_PER_IP = 2


async def _check_and_acquire(ip: str) -> tuple[bool, str]:
    """Atomically check rate + concurrent limits and acquire a session slot.
    Returns (allowed, reason)."""
    async with _rate_lock:
        now = time.time()
        cutoff = now - 3600
        history = _session_starts.get(ip, [])
        history = [t for t in history if t > cutoff]
        if not history:
            _session_starts.pop(ip, None)  # Evict stale IP keys
        else:
            _session_starts[ip] = history
        if len(history) >= _MAX_SESSIONS_PER_HOUR:
            return False, "rate_limited"
        if _active_sessions.get(ip, 0) >= _MAX_CONCURRENT_PER_IP:
            return False, "concurrent_limit"
        history.append(now)
        _session_starts[ip] = history
        _active_sessions[ip] = _active_sessions.get(ip, 0) + 1
        return True, ""


async def _release_session(ip: str) -> None:
    """Release a session slot."""
    async with _rate_lock:
        count = _active_sessions.get(ip, 1)
        if count <= 1:
            _active_sessions.pop(ip, None)
        else:
            _active_sessions[ip] = count - 1


_TRANSCRIPT_BUFFER_MAX = 100_000  # 100KB cap


@router.websocket("/ws/voice")
async def voice_agent_websocket(
    websocket: WebSocket,
    session_id: str = Query(default=""),
):
    """
    WebSocket endpoint that bridges client audio to Deepgram Voice Agent API.
    Unified PA — no mode parameter needed.
    """
    # Check if Deepgram is enabled
    if not settings.DEEPGRAM_ENABLED or not settings.DEEPGRAM_API_KEY:
        await websocket.close(code=4001, reason="Voice agent not available")
        return

    # Accept the WebSocket connection
    await websocket.accept()

    # Atomic rate + concurrent limit check
    client_ip = websocket.client.host if websocket.client else "unknown"
    allowed, reject_reason = await _check_and_acquire(client_ip)
    if not allowed:
        msg = "Too many voice sessions. Try again later." if reject_reason == "rate_limited" else "Maximum concurrent voice sessions reached."
        await websocket.send_json({"type": "error", "message": msg, "code": reject_reason})
        await websocket.close(code=4029)
        return

    # From here on, session slot is acquired — must release in finally
    try:
        await _run_voice_session(websocket, client_ip)
    finally:
        await _release_session(client_ip)


async def _run_voice_session(
    websocket: WebSocket,
    client_ip: str,
) -> None:
    """Core voice session logic — runs inside session slot guard."""
    # Initialize unified session (no mode)
    session = UnifiedVoiceSession()
    manager = VoiceSessionManager(
        db_pool=websocket.app.state.db_pool,
        openai_client=websocket.app.state.openai,
        scheduler=websocket.app.state.scheduler,
    )

    # Check daily budget
    if not await manager.check_daily_budget():
        await websocket.send_json({
            "type": "error",
            "message": "Daily voice minute budget exceeded.",
            "code": "budget_exceeded",
        })
        await websocket.close(code=4002)
        return

    # Initialize session — loads user context for prompt injection
    try:
        await manager.init_session(session)
    except Exception as e:
        logger.error(f"Session init failed: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Failed to initialize voice session.",
            "code": "init_failed",
        })
        await websocket.close(code=4003)
        return

    # Open connection to Deepgram
    deepgram_ws = None
    try:
        headers = {"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"}
        deepgram_ws = await websockets.connect(
            DEEPGRAM_AGENT_URL,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10,
        )
        logger.info(f"Connected to Deepgram Voice Agent API for session {session.session_id}")

        # Step 1: Wait for Welcome message
        welcome_msg = await asyncio.wait_for(deepgram_ws.recv(), timeout=10.0)
        if isinstance(welcome_msg, str):
            welcome_data = json.loads(welcome_msg)
            if welcome_data.get("type") != "Welcome":
                logger.warning(f"Expected Welcome, got: {welcome_data.get('type')}")

        # Step 2: Send Settings configuration
        config = manager.build_settings_config(session)
        await deepgram_ws.send(json.dumps(config))

        # Step 3: Wait for SettingsApplied before sending audio
        settings_msg = await asyncio.wait_for(deepgram_ws.recv(), timeout=10.0)
        if isinstance(settings_msg, str):
            settings_data = json.loads(settings_msg)
            if settings_data.get("type") == "Error":
                logger.error(f"Deepgram rejected settings: {settings_data}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Voice agent configuration rejected.",
                    "code": "settings_rejected",
                })
                await websocket.close(code=4003)
                return
            logger.info(f"Deepgram settings applied: {settings_data.get('type')}")

        # Notify client that we're ready
        await websocket.send_json({"type": "ready", "session_id": session.session_id})

        # Run bidirectional forwarding
        max_duration = settings.MAX_VOICE_SESSION_MINUTES * 60
        warning_sent = False

        async def client_to_deepgram():
            """Forward audio and control messages from client to Deepgram."""
            nonlocal warning_sent
            try:
                while True:
                    # Check max duration
                    elapsed = time.monotonic() - session.started_at
                    if elapsed >= max_duration:
                        logger.info(f"Session {session.session_id} hit max duration")
                        # Trigger end session
                        end_result = await manager.handle_function_call(session, "end_session", {})
                        await websocket.send_json({
                            "type": "session_end",
                            "summary": json.loads(end_result),
                        })
                        return

                    if not warning_sent and max_duration > 180 and elapsed >= max_duration - 180:
                        warning_sent = True
                        # Inject warning message
                        try:
                            inject_msg = {
                                "type": "InjectAgentMessage",
                                "message": f"We've been going for {int(elapsed // 60)} minutes. I'll wrap up in {int((max_duration - elapsed) // 60)} minutes.",
                            }
                            await deepgram_ws.send(json.dumps(inject_msg))
                        except Exception:
                            pass

                    msg = await websocket.receive()
                    if msg.get("type") == "websocket.disconnect":
                        return

                    if "bytes" in msg and msg["bytes"]:
                        # Binary audio — forward to Deepgram
                        await deepgram_ws.send(msg["bytes"])
                    elif "text" in msg and msg["text"]:
                        try:
                            data = json.loads(msg["text"])
                        except json.JSONDecodeError:
                            logger.warning("Malformed JSON from client, ignoring")
                            continue
                        if data.get("type") == "end":
                            # User requested end
                            end_result = await manager.handle_function_call(session, "end_session", {})
                            await websocket.send_json({
                                "type": "session_end",
                                "summary": json.loads(end_result),
                            })
                            return
            except WebSocketDisconnect:
                logger.info(f"Client disconnected from session {session.session_id}")
            except Exception as e:
                logger.error(f"client_to_deepgram error: {e}")

        async def deepgram_to_client():
            """Forward audio and events from Deepgram to client, intercept function calls."""
            try:
                async for message in deepgram_ws:
                    if isinstance(message, bytes):
                        # Binary TTS audio — forward to client
                        try:
                            await websocket.send_bytes(message)
                        except Exception:
                            return
                    elif isinstance(message, str):
                        try:
                            data = json.loads(message)
                        except json.JSONDecodeError:
                            logger.warning("Malformed JSON from Deepgram, ignoring")
                            continue
                        msg_type = data.get("type", "")

                        if msg_type == "FunctionCallRequest":
                            # Intercept function calls from the functions array
                            fn_calls = data.get("functions", [])
                            for fn_call in fn_calls:
                                fn_name = fn_call.get("name", "")
                                fn_id = fn_call.get("id", "")
                                # arguments is a JSON string per the API
                                raw_args = fn_call.get("arguments", "{}")
                                try:
                                    fn_input = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                                except json.JSONDecodeError:
                                    fn_input = {}

                                logger.info(f"Function call: {fn_name}({fn_input})")

                                result = await manager.handle_function_call(
                                    session, fn_name, fn_input,
                                )

                                # Send result back to Deepgram using correct field names
                                response = {
                                    "type": "FunctionCallResponse",
                                    "id": fn_id,
                                    "name": fn_name,
                                    "content": result,
                                }
                                await deepgram_ws.send(json.dumps(response))

                                # Also notify client about the function result
                                try:
                                    await websocket.send_json({
                                        "type": "function_result",
                                        "name": fn_name,
                                        "result": json.loads(result),
                                    })
                                except Exception:
                                    pass

                        elif msg_type == "ConversationText":
                            # Transcript event
                            role = data.get("role", "")
                            content = data.get("content", "")

                            # Accumulate user transcript for potential capture
                            if role == "user":
                                if len(session.transcript_buffer) < _TRANSCRIPT_BUFFER_MAX:
                                    session.transcript_buffer += " " + content

                            try:
                                await websocket.send_json({
                                    "type": "transcript",
                                    "role": role,
                                    "text": content,
                                })
                            except Exception:
                                return

                        elif msg_type == "UserStartedSpeaking":
                            try:
                                await websocket.send_json({
                                    "type": "status",
                                    "state": "user_speaking",
                                })
                            except Exception:
                                return

                        elif msg_type == "AgentThinking":
                            try:
                                await websocket.send_json({
                                    "type": "status",
                                    "state": "thinking",
                                })
                            except Exception:
                                return

                        elif msg_type == "AgentAudioDone":
                            try:
                                await websocket.send_json({
                                    "type": "status",
                                    "state": "agent_done_speaking",
                                })
                            except Exception:
                                return

                        elif msg_type == "Error":
                            logger.error(f"Deepgram error: {data}")
                            try:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": "Voice agent encountered an error",
                                    "code": "deepgram_error",
                                })
                            except Exception:
                                return

            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Deepgram connection closed for session {session.session_id}")
            except Exception as e:
                logger.error(f"deepgram_to_client error: {e}")

        # Run both directions concurrently
        tasks = [
            asyncio.create_task(client_to_deepgram()),
            asyncio.create_task(deepgram_to_client()),
        ]
        # Wait for either to finish (whichever completes first cancels the other)
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except websockets.exceptions.InvalidStatusCode as e:
        logger.error(f"Deepgram auth/connection failed: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Voice agent authentication failed",
                "code": "auth_failed",
            })
        except Exception:
            pass
    except asyncio.TimeoutError:
        logger.error("Deepgram connection timed out")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Voice agent connection timed out",
                "code": "timeout",
            })
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Voice session error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Voice session error",
                "code": "internal_error",
            })
        except Exception:
            pass
    finally:
        # Cleanup

        if deepgram_ws:
            try:
                await deepgram_ws.close()
            except Exception:
                pass

        # Log session for cost tracking
        try:
            await manager.log_session(session)
        except Exception as e:
            logger.error(f"Session logging failed: {e}")

        # Close client websocket if still open
        try:
            await websocket.close()
        except Exception:
            pass

        logger.info(
            f"Voice session {session.session_id} ended: "
            f"mode={session.mode}, duration={int(time.monotonic() - session.started_at)}s"
        )
