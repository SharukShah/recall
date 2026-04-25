"""
Unit tests for VoiceSessionManager — function dispatch, state management, config generation.
Uses mocks for DB/OpenAI/Scheduler. No real Deepgram connection.
"""
import asyncio
import json
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Must set env vars before importing config
import os
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")

from services.voice_service import (
    VoiceSession,
    VoiceSessionManager,
    _ALLOWED_FUNCTIONS,
    COMMON_FUNCTIONS,
    CAPTURE_FUNCTIONS,
    REVIEW_FUNCTIONS,
    TEACH_FUNCTIONS,
)


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    conn = AsyncMock()
    acm = AsyncMock()
    acm.__aenter__ = AsyncMock(return_value=conn)
    acm.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = acm
    pool._conn = conn  # expose for tests that need it
    return pool


@pytest.fixture
def mock_openai():
    return AsyncMock()


@pytest.fixture
def mock_scheduler():
    return MagicMock()


@pytest.fixture
def manager(mock_pool, mock_openai, mock_scheduler):
    return VoiceSessionManager(mock_pool, mock_openai, mock_scheduler)


# =========================================================================
# 1. Settings Configuration Tests
# =========================================================================

class TestBuildSettingsConfig:
    """Verify Deepgram Settings message matches API spec."""

    def test_settings_type_is_correct(self, manager):
        session = VoiceSession(mode="capture")
        config = manager.build_settings_config(session)
        assert config["type"] == "Settings"

    def test_audio_input_format(self, manager):
        session = VoiceSession(mode="capture")
        config = manager.build_settings_config(session)
        assert config["audio"]["input"]["encoding"] == "linear16"
        assert config["audio"]["input"]["sample_rate"] == 16000

    def test_audio_output_format(self, manager):
        session = VoiceSession(mode="capture")
        config = manager.build_settings_config(session)
        assert config["audio"]["output"]["encoding"] == "linear16"
        assert config["audio"]["output"]["sample_rate"] == 24000
        assert config["audio"]["output"]["container"] == "none"

    def test_listen_provider_nested(self, manager):
        session = VoiceSession(mode="capture")
        config = manager.build_settings_config(session)
        listen = config["agent"]["listen"]
        assert "provider" in listen
        assert listen["provider"]["type"] == "deepgram"
        assert "model" in listen["provider"]
        assert "keyterms" in listen["provider"]

    def test_think_provider_nested(self, manager):
        session = VoiceSession(mode="capture")
        config = manager.build_settings_config(session)
        think = config["agent"]["think"]
        assert think["provider"]["type"] == "open_ai"
        assert "model" in think["provider"]
        assert "temperature" in think["provider"]
        # Should use "prompt" not "instructions"
        assert "prompt" in think
        assert "instructions" not in think
        # max_tokens should NOT be in provider (Deepgram doesn't support it)
        assert "max_tokens" not in think["provider"]

    def test_speak_provider_nested(self, manager):
        session = VoiceSession(mode="capture")
        config = manager.build_settings_config(session)
        speak = config["agent"]["speak"]
        assert "provider" in speak
        assert speak["provider"]["type"] == "deepgram"
        assert "model" in speak["provider"]

    def test_functions_included_per_mode(self, manager):
        for mode_name in ("capture", "review", "teach"):
            session = VoiceSession(mode=mode_name)
            config = manager.build_settings_config(session)
            fn_names = {f["name"] for f in config["agent"]["think"]["functions"]}
            # Common functions always present
            assert "search_knowledge" in fn_names
            assert "end_session" in fn_names

    def test_capture_mode_has_finish_capture(self, manager):
        session = VoiceSession(mode="capture")
        config = manager.build_settings_config(session)
        fn_names = {f["name"] for f in config["agent"]["think"]["functions"]}
        assert "finish_capture" in fn_names
        assert "save_why_it_matters" in fn_names

    def test_review_mode_has_review_functions(self, manager):
        session = VoiceSession(mode="review")
        config = manager.build_settings_config(session)
        fn_names = {f["name"] for f in config["agent"]["think"]["functions"]}
        assert "get_next_question" in fn_names
        assert "evaluate_answer" in fn_names
        assert "rate_question" in fn_names

    def test_teach_mode_has_teach_functions(self, manager):
        session = VoiceSession(mode="teach")
        config = manager.build_settings_config(session)
        fn_names = {f["name"] for f in config["agent"]["think"]["functions"]}
        assert "get_current_teach_chunk" in fn_names
        assert "submit_teach_answer" in fn_names


# =========================================================================
# 2. Function Whitelist Tests
# =========================================================================

class TestFunctionWhitelist:
    """Verify function calls are gated by mode."""

    @pytest.mark.asyncio
    async def test_capture_rejects_review_functions(self, manager):
        session = VoiceSession(mode="capture")
        result = json.loads(await manager.handle_function_call(session, "get_next_question", {}))
        assert "error" in result
        assert "not available" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_review_rejects_capture_functions(self, manager):
        session = VoiceSession(mode="review")
        result = json.loads(await manager.handle_function_call(session, "finish_capture", {}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_teach_rejects_review_functions(self, manager):
        session = VoiceSession(mode="teach")
        result = json.loads(await manager.handle_function_call(session, "rate_question", {}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_function_rejected(self, manager):
        session = VoiceSession(mode="capture")
        result = json.loads(await manager.handle_function_call(session, "hack_system", {}))
        assert "error" in result

    def test_all_modes_allow_search_and_end(self):
        for mode_name in ("capture", "review", "teach"):
            allowed = _ALLOWED_FUNCTIONS[mode_name]
            assert "search_knowledge" in allowed
            assert "end_session" in allowed


# =========================================================================
# 3. Review Flow Tests (get_next_question, evaluate, rate)
# =========================================================================

class TestReviewFlow:
    """Test the review state machine: get → evaluate → rate → advance."""

    def _make_review_session(self) -> VoiceSession:
        session = VoiceSession(mode="review")
        session.review_queue = [
            {"question_id": "00000000-0000-0000-0000-000000000001", "question_text": "What is X?", "question_type": "recall", "mnemonic_hint": None, "technique_used": None},
            {"question_id": "00000000-0000-0000-0000-000000000002", "question_text": "What is Y?", "question_type": "recall", "mnemonic_hint": None, "technique_used": None},
            {"question_id": "00000000-0000-0000-0000-000000000003", "question_text": "What is Z?", "question_type": "recall", "mnemonic_hint": None, "technique_used": None},
        ]
        session.review_index = 0
        return session

    def test_get_next_question_returns_first(self, manager):
        session = self._make_review_session()
        result = manager._get_next_question(session)
        assert result["done"] is False
        assert result["question_id"] == "00000000-0000-0000-0000-000000000001"
        assert result["question_number"] == 0
        assert result["total_questions"] == 3

    def test_get_next_question_is_idempotent(self, manager):
        """Calling get_next_question twice without rating should return the same question."""
        session = self._make_review_session()
        r1 = manager._get_next_question(session)
        r2 = manager._get_next_question(session)
        assert r1["question_id"] == r2["question_id"]
        assert session.review_index == 0  # Not advanced

    @pytest.mark.asyncio
    async def test_rate_advances_index(self, manager):
        session = self._make_review_session()

        # Mock the ReviewService.rate call
        with patch("services.voice_service.ReviewService") as MockReviewSvc:
            mock_svc = MockReviewSvc.return_value
            mock_svc.rate = AsyncMock(return_value=MagicMock(
                next_due="2026-04-20T00:00:00Z",
                interval_days=2,
                state_label="learning",
            ))

            result = await manager._rate_question("00000000-0000-0000-0000-000000000001", 3, session)
            assert "error" not in result
            assert session.review_index == 1
            assert "00000000-0000-0000-0000-000000000001" in session.rated_question_ids

    @pytest.mark.asyncio
    async def test_duplicate_rating_rejected(self, manager):
        session = self._make_review_session()
        session.rated_question_ids.add("00000000-0000-0000-0000-000000000001")

        result = await manager._rate_question("00000000-0000-0000-0000-000000000001", 3, session)
        assert "error" in result
        assert "already rated" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_question_id_rejected_evaluate(self, manager):
        session = self._make_review_session()
        result = await manager._evaluate_answer("nonexistent", "my answer", session)
        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_question_id_rejected_rate(self, manager):
        session = self._make_review_session()
        result = await manager._rate_question("nonexistent", 3, session)
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_all_reviewed_returns_done(self, manager):
        session = self._make_review_session()
        session.review_index = 3  # Past end
        result = manager._get_next_question(session)
        assert result["done"] is True
        assert "All questions reviewed" in result["message"]

    @pytest.mark.asyncio
    async def test_rate_clamps_values(self, manager):
        session = self._make_review_session()
        with patch("services.voice_service.ReviewService") as MockReviewSvc:
            mock_svc = MockReviewSvc.return_value
            mock_svc.rate = AsyncMock(return_value=MagicMock(
                next_due="2026-04-20", interval_days=1, state_label="learning",
            ))

            # Rating 0 should clamp to 1
            result = await manager._rate_question("00000000-0000-0000-0000-000000000001", 0, session)
            call_args = mock_svc.rate.call_args[0][0]
            assert call_args.rating == 1

    @pytest.mark.asyncio
    async def test_rate_clamps_high_values(self, manager):
        session = self._make_review_session()
        with patch("services.voice_service.ReviewService") as MockReviewSvc:
            mock_svc = MockReviewSvc.return_value
            mock_svc.rate = AsyncMock(return_value=MagicMock(
                next_due="2026-04-20", interval_days=1, state_label="learning",
            ))
            result = await manager._rate_question("00000000-0000-0000-0000-000000000001", 99, session)
            call_args = mock_svc.rate.call_args[0][0]
            assert call_args.rating == 4


# =========================================================================
# 4. Capture Flow Tests
# =========================================================================

class TestCaptureFlow:
    """Test capture mode: transcript accumulation, finish, double-processing guard."""

    @pytest.mark.asyncio
    async def test_finish_capture_clears_buffer(self, manager):
        session = VoiceSession(mode="capture")
        session.transcript_buffer = "The mitochondria is the powerhouse of the cell"

        with patch("services.voice_service.CaptureService") as MockCaptureSvc:
            mock_svc = MockCaptureSvc.return_value
            mock_svc.process = AsyncMock(return_value=MagicMock(
                capture_id="abc-123",
                facts_count=3,
                questions_count=2,
                status="processed",
            ))
            result = await manager._finish_capture(session, "explicit transcript")
            assert result["facts_count"] == 3
            assert session.transcript_buffer == ""
            assert session.capture_processed is True

    @pytest.mark.asyncio
    async def test_end_session_skips_if_already_captured(self, manager):
        session = VoiceSession(mode="capture")
        session.transcript_buffer = "leftover text"
        session.capture_processed = True

        result = await manager._end_session(session)
        assert result["ended"] is True
        assert "capture_result" not in result  # Should NOT re-process

    @pytest.mark.asyncio
    async def test_end_session_processes_remaining_transcript(self, manager):
        session = VoiceSession(mode="capture")
        session.transcript_buffer = "unprocessed text"
        session.capture_processed = False

        with patch("services.voice_service.CaptureService") as MockCaptureSvc:
            mock_svc = MockCaptureSvc.return_value
            mock_svc.process = AsyncMock(return_value=MagicMock(
                capture_id="xyz-456",
                facts_count=1,
                questions_count=1,
                status="processed",
            ))
            result = await manager._end_session(session)
            assert result["ended"] is True
            assert result["capture_result"]["facts_count"] == 1

    @pytest.mark.asyncio
    async def test_finish_capture_empty_transcript(self, manager):
        session = VoiceSession(mode="capture")
        session.transcript_buffer = ""
        result = await manager._finish_capture(session, "")
        assert "error" in result
        assert result["facts_count"] == 0


# =========================================================================
# 5. Session Duration Tests
# =========================================================================

class TestSessionDuration:
    """Verify time.monotonic is used consistently."""

    def test_session_started_at_uses_monotonic(self):
        before = time.monotonic()
        session = VoiceSession()
        after = time.monotonic()
        assert before <= session.started_at <= after

    @pytest.mark.asyncio
    async def test_end_session_duration_uses_monotonic(self, manager):
        session = VoiceSession(mode="review")
        session.started_at = time.monotonic() - 120  # 2 minutes ago

        result = await manager._end_session(session)
        # Duration should be ~120 seconds, definitely not negative or huge
        assert 118 <= result["duration_seconds"] <= 125


# =========================================================================
# 6. Teach Mode Tests
# =========================================================================

class TestTeachMode:
    def test_get_chunk_no_session(self, manager):
        session = VoiceSession(mode="teach")
        result = manager._get_current_teach_chunk(session)
        assert "error" in result

    def test_get_chunk_returns_data(self, manager):
        session = VoiceSession(mode="teach")
        session.teach_current_chunk = {
            "chunk_title": "Introduction",
            "chunk_content": "Content here",
            "chunk_analogy": "Like a...",
            "recall_question": "What is...?",
        }
        session.teach_chunk_index = 0
        session.teach_total_chunks = 3
        result = manager._get_current_teach_chunk(session)
        assert result["chunk_title"] == "Introduction"
        assert result["total_chunks"] == 3


# =========================================================================
# 7. Error Sanitization Tests
# =========================================================================

class TestErrorSanitization:
    """Verify no raw exceptions leak to clients."""

    @pytest.mark.asyncio
    async def test_handle_function_call_sanitizes_errors(self, manager):
        session = VoiceSession(mode="capture")
        # search_knowledge will raise because mock pool isn't fully set up
        with patch.object(manager, "_dispatch", side_effect=RuntimeError("DB connection refused: password=xxx")):
            result = json.loads(await manager.handle_function_call(session, "search_knowledge", {"query": "test"}))
            assert "error" in result
            # Must NOT contain the raw exception with password
            assert "password" not in result["error"]
            assert "DB connection" not in result["error"]
            assert result["error"] == "Function call failed. Please try again."

    @pytest.mark.asyncio
    async def test_save_why_it_matters_sanitizes_error(self, manager):
        # Invalid UUID should trigger exception
        result = await manager._save_why_it_matters("not-a-uuid", "important")
        assert result["saved"] is False
        # Should NOT contain "badly formed hexadecimal UUID string"
        assert "badly formed" not in result.get("error", "")
        assert result["error"] == "Failed to save reflection"


# =========================================================================
# 8. Daily Budget Tests
# =========================================================================

class TestDailyBudget:
    @pytest.mark.asyncio
    async def test_budget_fails_closed_on_db_error(self, manager):
        """If DB query fails, budget check should DENY (return False)."""
        manager.db_pool.acquire.side_effect = Exception("Connection refused")
        result = await manager.check_daily_budget()
        assert result is False  # Fail closed

    @pytest.mark.asyncio
    async def test_budget_under_limit_returns_true(self, manager, mock_pool):
        mock_pool._conn.fetchval = AsyncMock(return_value=100)  # 100 seconds used today
        result = await manager.check_daily_budget()
        assert result is True

    @pytest.mark.asyncio
    async def test_budget_over_limit_returns_false(self, manager, mock_pool):
        # 60 min * 60 sec = 3600 seconds, return more than that
        mock_pool._conn.fetchval = AsyncMock(return_value=4000)
        result = await manager.check_daily_budget()
        assert result is False
