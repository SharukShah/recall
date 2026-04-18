"""
Voice router — TTS audio generation for voice review.
POST /tts → generate speech audio from text using OpenAI TTS-1.
"""
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.rate_limiter import rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str = Field(default="nova")


@router.post("/tts", dependencies=[Depends(rate_limit(10))])
async def text_to_speech(body: TTSRequest, request: Request):
    """Generate TTS audio using OpenAI TTS-1. Returns MP3 bytes."""
    allowed_voices = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
    if body.voice not in allowed_voices:
        raise HTTPException(status_code=400, detail=f"Voice must be one of: {allowed_voices}")

    try:
        response = await request.app.state.openai.audio.speech.create(
            model="tts-1",
            voice=body.voice,
            input=body.text,
            response_format="mp3",
        )
        audio_bytes = response.content
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Length": str(len(audio_bytes))},
        )
    except Exception as e:
        logger.error(f"TTS generation failed: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="TTS generation failed")
