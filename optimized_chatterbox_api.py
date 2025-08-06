from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import uuid
import os
import asyncio
import time

router = APIRouter()

class SynthesisRequest(BaseModel):
    text: str

# ChatterboxTTS service configuration
CHATTERBOX_SERVICE_URL = "http://localhost:8001"
REQUEST_TIMEOUT = 30  # seconds

async def check_service_health():
    """Check if the ChatterboxTTS service is running"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{CHATTERBOX_SERVICE_URL}/health")
            return response.status_code == 200 and response.json().get("model_loaded", False)
    except Exception:
        return False

@router.post("/indian_accent")
async def synthesize_with_chatterbox(text_input: SynthesisRequest):
    """Optimized synthesis using persistent ChatterboxTTS service"""
    text = text_input.text
    filename = f"cloned_output_{uuid.uuid4().hex[:8]}.wav"
    output_path = f"/var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions/{filename}"

    try:
        start_time = time.time()
        
        # Check if service is healthy
        if not await check_service_health():
            raise HTTPException(
                status_code=503, 
                detail="ChatterboxTTS service is not available or model not loaded"
            )

        # Make request to persistent service
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{CHATTERBOX_SERVICE_URL}/generate",
                json={
                    "text": text,
                    "output_path": "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions/cloned_output.wav"
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"TTS service error: {response.text}")
            
            result = response.json()

        # Rename to unique file name
        default_output = "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions/cloned_output.wav"
        if os.path.exists(default_output):
            os.rename(default_output, output_path)
        else:
            raise HTTPException(status_code=500, detail="Generated audio file not found")

        total_time = time.time() - start_time
        
        return {
            "status": "success",
            "download_url": f"/sessions/{filename}",
            "generation_time": result.get("generation_time", 0),
            "total_time": total_time,
            "message": "✅ Indian accent TTS generated successfully"
        }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, 
            detail="ChatterboxTTS service timeout - generation took too long"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Failed to connect to ChatterboxTTS service: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/health")
async def api_health():
    """Check the health of both this API and the ChatterboxTTS service"""
    service_healthy = await check_service_health()
    
    return {
        "api_status": "healthy",
        "chatterbox_service": "healthy" if service_healthy else "unhealthy",
        "overall_status": "healthy" if service_healthy else "degraded"
    }