import os
import io
import asyncio
import edge_tts
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="Edge TTS API",
    description="Free Microsoft Edge TTS hosted on Vercel. No API key from Microsoft needed.",
    version="1.0.0",
)

API_KEY = os.environ.get("API_KEY", "")


def verify_key(x_api_key: Optional[str]):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key. Pass it as X-API-Key header.")


class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-AriaNeural"
    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"


@app.get("/")
def root():
    return {
        "service": "Edge TTS API",
        "docs": "/docs",
        "endpoints": {
            "POST /tts": "Generate speech (returns MP3 audio)",
            "GET /tts": "Generate speech via query params",
            "GET /voices": "List all available voices",
        },
    }


@app.get("/voices")
async def list_voices(x_api_key: Optional[str] = Header(default=None)):
    verify_key(x_api_key)
    voices = await edge_tts.list_voices()
    return JSONResponse(content=voices)


async def _synthesize(text: str, voice: str, rate: str, volume: str, pitch: str) -> bytes:
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume=volume,
        pitch=pitch,
    )
    audio_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])
    audio_buffer.seek(0)
    return audio_buffer.read()


@app.post("/tts")
async def tts_post(request: TTSRequest, x_api_key: Optional[str] = Header(default=None)):
    verify_key(x_api_key)
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    try:
        audio_bytes = await _synthesize(
            text=request.text,
            voice=request.voice,
            rate=request.rate,
            volume=request.volume,
            pitch=request.pitch,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"},
    )


@app.get("/tts")
async def tts_get(
    text: str = Query(..., description="Text to convert to speech"),
    voice: str = Query("en-US-AriaNeural", description="Voice name"),
    rate: str = Query("+0%", description="Speed e.g. +20% or -10%"),
    volume: str = Query("+0%", description="Volume e.g. +10% or -20%"),
    pitch: str = Query("+0Hz", description="Pitch e.g. +50Hz or -30Hz"),
    x_api_key: Optional[str] = Header(default=None),
):
    verify_key(x_api_key)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    try:
        audio_bytes = await _synthesize(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"},
    )
