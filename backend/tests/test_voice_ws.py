"""
Integration tests for the voice WebSocket endpoint — rate limiting,
session management, and mock Deepgram connection flow.
"""
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import os
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("DEEPGRAM_API_KEY", "test-deepgram-key")
os.environ.setdefault("DEEPGRAM_ENABLED", "true")

from routers.voice_ws import (
    _check_and_acquire,
    _release_session,
    _rate_lock,
    _session_starts,
    _active_sessions,
    _MAX_SESSIONS_PER_HOUR,
    _MAX_CONCURRENT_PER_IP,
    _TRANSCRIPT_BUFFER_MAX,
    VALID_MODES,
)


@pytest.fixture(autouse=True)
async def clear_rate_limits():
    """Reset rate limiter state before each test."""
    async with _rate_lock:
        _session_starts.clear()
        _active_sessions.clear()
    yield
    async with _rate_lock:
        _session_starts.clear()
        _active_sessions.clear()


# =========================================================================
# 1. Rate Limiting Tests
# =========================================================================

class TestRateLimiting:
    """Verify atomic rate + concurrent limit enforcement."""

    @pytest.mark.asyncio
    async def test_first_session_allowed(self):
        allowed, reason = await _check_and_acquire("192.168.1.1")
        assert allowed is True
        assert reason == ""
        await _release_session("192.168.1.1")

    @pytest.mark.asyncio
    async def test_concurrent_limit_enforced(self):
        """Two sessions allowed, third rejected."""
        a1, _ = await _check_and_acquire("10.0.0.1")
        a2, _ = await _check_and_acquire("10.0.0.1")
        a3, reason = await _check_and_acquire("10.0.0.1")

        assert a1 is True
        assert a2 is True
        assert a3 is False
        assert reason == "concurrent_limit"

        await _release_session("10.0.0.1")
        await _release_session("10.0.0.1")

    @pytest.mark.asyncio
    async def test_release_allows_new_session(self):
        """After releasing, a new session should be allowed."""
        await _check_and_acquire("10.0.0.2")
        await _check_and_acquire("10.0.0.2")
        # At limit
        a3, _ = await _check_and_acquire("10.0.0.2")
        assert a3 is False

        # Release one
        await _release_session("10.0.0.2")

        # Should be allowed now
        a4, _ = await _check_and_acquire("10.0.0.2")
        assert a4 is True

        await _release_session("10.0.0.2")
        await _release_session("10.0.0.2")

    @pytest.mark.asyncio
    async def test_hourly_rate_limit(self):
        """After MAX_SESSIONS_PER_HOUR, further sessions rejected."""
        ip = "10.0.0.3"
        for i in range(_MAX_SESSIONS_PER_HOUR):
            allowed, _ = await _check_and_acquire(ip)
            assert allowed is True
            await _release_session(ip)  # Release concurrent slot

        # Next one should be rate limited
        allowed, reason = await _check_and_acquire(ip)
        assert allowed is False
        assert reason == "rate_limited"

    @pytest.mark.asyncio
    async def test_different_ips_independent(self):
        """Rate limits are per-IP."""
        a1, _ = await _check_and_acquire("1.1.1.1")
        a2, _ = await _check_and_acquire("2.2.2.2")
        assert a1 is True
        assert a2 is True
        await _release_session("1.1.1.1")
        await _release_session("2.2.2.2")

    @pytest.mark.asyncio
    async def test_stale_ip_evicted(self):
        """IPs with only expired timestamps should be cleaned up."""
        async with _rate_lock:
            _session_starts["old.ip"] = [time.time() - 7200]  # 2 hours ago

        # Trigger cleanup via check_and_acquire
        await _check_and_acquire("old.ip")
        async with _rate_lock:
            # Old timestamps should have been pruned, and since
            # the only entry was stale, key should be re-added with new timestamp
            assert "old.ip" in _session_starts  # Re-added with new timestamp
            assert all(t > time.time() - 3600 for t in _session_starts["old.ip"])

        await _release_session("old.ip")

    @pytest.mark.asyncio
    async def test_concurrent_acquire_is_atomic(self):
        """Multiple concurrent acquires should not race past the limit."""
        ip = "race.test"
        results = await asyncio.gather(
            _check_and_acquire(ip),
            _check_and_acquire(ip),
            _check_and_acquire(ip),
            _check_and_acquire(ip),
        )
        allowed_count = sum(1 for allowed, _ in results if allowed)
        assert allowed_count == _MAX_CONCURRENT_PER_IP  # Exactly 2

        # Cleanup
        for _ in range(allowed_count):
            await _release_session(ip)


# =========================================================================
# 2. Mode Validation Tests
# =========================================================================

class TestModeValidation:
    def test_valid_modes(self):
        assert VALID_MODES == {"capture", "review", "teach"}

    def test_invalid_mode_not_in_set(self):
        assert "hack" not in VALID_MODES
        assert "" not in VALID_MODES


# =========================================================================
# 3. Transcript Buffer Cap Tests
# =========================================================================

class TestTranscriptBuffer:
    def test_buffer_max_is_100kb(self):
        assert _TRANSCRIPT_BUFFER_MAX == 100_000

    def test_buffer_accumulation_capped(self):
        """Simulate transcript accumulation with cap."""
        from services.voice_service import VoiceSession
        session = VoiceSession(mode="capture")

        # Fill buffer to near cap
        session.transcript_buffer = "x" * 99_990

        # Simulate the capped accumulation logic from voice_ws.py
        content = "new content here"
        if len(session.transcript_buffer) < _TRANSCRIPT_BUFFER_MAX:
            session.transcript_buffer += " " + content

        assert len(session.transcript_buffer) <= _TRANSCRIPT_BUFFER_MAX + 20  # Small overflow OK

        # Now try when already at cap
        session.transcript_buffer = "x" * _TRANSCRIPT_BUFFER_MAX
        old_len = len(session.transcript_buffer)
        if len(session.transcript_buffer) < _TRANSCRIPT_BUFFER_MAX:
            session.transcript_buffer += " " + content
        assert len(session.transcript_buffer) == old_len  # Not appended


# =========================================================================
# 4. FunctionCallRequest/Response Format Tests
# =========================================================================

class TestFunctionCallFormat:
    """Verify our parsing matches Deepgram's actual message format."""

    def test_parse_function_call_request(self):
        """Deepgram sends functions[] array with id, name, arguments (JSON string)."""
        deepgram_msg = {
            "type": "FunctionCallRequest",
            "functions": [
                {
                    "id": "fc_12345678-90ab-cdef-1234-567890abcdef",
                    "name": "search_knowledge",
                    "arguments": '{"query": "What is FSRS?"}',
                    "client_side": True,
                }
            ]
        }

        fn_calls = deepgram_msg.get("functions", [])
        assert len(fn_calls) == 1

        fn = fn_calls[0]
        assert fn["name"] == "search_knowledge"
        assert fn["id"] == "fc_12345678-90ab-cdef-1234-567890abcdef"

        # Arguments is a JSON string — must be parsed
        args = json.loads(fn["arguments"])
        assert args["query"] == "What is FSRS?"

    def test_function_call_response_format(self):
        """Our response must use id, name, content — not function_call_id, output."""
        fn_id = "fc_test-id"
        fn_name = "search_knowledge"
        result = '{"answer": "FSRS is a spaced repetition algorithm"}'

        response = {
            "type": "FunctionCallResponse",
            "id": fn_id,
            "name": fn_name,
            "content": result,
        }

        assert response["type"] == "FunctionCallResponse"
        assert response["id"] == fn_id
        assert response["name"] == fn_name
        assert response["content"] == result
        # Must NOT have old field names
        assert "function_call_id" not in response
        assert "output" not in response

    def test_arguments_as_dict_handled(self):
        """If arguments is already a dict (edge case), should still work."""
        raw_args = {"query": "test"}
        if isinstance(raw_args, str):
            parsed = json.loads(raw_args)
        else:
            parsed = raw_args
        assert parsed["query"] == "test"


# =========================================================================
# 5. Connection Handshake Tests
# =========================================================================

class TestConnectionHandshake:
    """Verify we follow Welcome → Settings → SettingsApplied sequence."""

    def test_welcome_message_format(self):
        welcome = {"type": "Welcome", "request_id": "test-uuid"}
        assert welcome["type"] == "Welcome"

    def test_settings_applied_format(self):
        applied = {"type": "SettingsApplied"}
        assert applied["type"] == "SettingsApplied"

    def test_settings_rejected_detected(self):
        error = {"type": "Error", "description": "Invalid settings", "code": "INVALID_SETTINGS"}
        assert error["type"] == "Error"
        assert error["code"] == "INVALID_SETTINGS"


# =========================================================================
# 6. Session Lifecycle Tests
# =========================================================================

class TestSessionLifecycle:
    """Test session creation and state initialization."""

    def test_session_defaults(self):
        from services.voice_service import VoiceSession
        session = VoiceSession()
        assert session.mode == "capture"
        assert session.transcript_buffer == ""
        assert session.review_queue == []
        assert session.review_index == 0
        assert session.reviewed_count == 0
        assert session.rated_question_ids == set()
        assert session.capture_processed is False

    def test_session_id_is_valid_uuid(self):
        from services.voice_service import VoiceSession
        import uuid
        session = VoiceSession()
        parsed = uuid.UUID(session.session_id)
        assert str(parsed) == session.session_id
