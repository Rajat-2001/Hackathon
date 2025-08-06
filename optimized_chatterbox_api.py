from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid
import os
import aiohttp
import asyncio
import time

router = APIRouter()

class SynthesisRequest(BaseModel):
    text: str

# Configuration
CHATTERBOX_SERVER_URL = "http://localhost:8001"
CONNECTION_TIMEOUT = 30  # seconds
REQUEST_TIMEOUT = 60    # seconds

async def call_chatterbox_server(text: str, filename: str = None):
    """
    Call the persistent chatterbox server instead of subprocess
    """
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(
                total=REQUEST_TIMEOUT,
                connect=CONNECTION_TIMEOUT
            )
        ) as session:
            payload = {
                "text": text,
                "output_filename": filename
            }
            
            start_time = time.time()
            async with session.post(f"{CHATTERBOX_SERVER_URL}/synthesize", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    elapsed_time = time.time() - start_time
                    print(f"⚡ Chatterbox synthesis completed in {elapsed_time:.2f} seconds")
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"Server returned {response.status}: {error_text}")
                    
    except aiohttp.ClientError as e:
        raise Exception(f"Failed to connect to chatterbox server: {str(e)}")
    except asyncio.TimeoutError:
        raise Exception("Chatterbox server request timed out")

@router.post("/indian_accent")
async def synthesize_with_chatterbox(text_input: SynthesisRequest):
    """
    Optimized synthesis using persistent server
    """
    text = text_input.text
    filename = f"cloned_output_{uuid.uuid4().hex[:8]}.wav"
    
    try:
        # Call the persistent server
        result = await call_chatterbox_server(text, filename)
        
        if result["status"] == "success":
            return {
                "status": "success",
                "download_url": f"/sessions/{result['filename']}",
                "processing_time": "optimized"
            }
        else:
            raise HTTPException(status_code=500, detail="Chatterbox synthesis failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatterbox TTS failed: {str(e)}")

@router.get("/health")
async def check_chatterbox_health():
    """
    Check if the chatterbox server is healthy
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CHATTERBOX_SERVER_URL}/health") as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    return {"status": "unhealthy", "message": f"Server returned {response.status}"}
    except Exception as e:
        return {"status": "unreachable", "message": str(e)}