#!/usr/bin/env python3
"""
Persistent ChatterboxTTS Service
Keeps the model loaded in memory for fast inference
Run this in your chatter_box conda environment
"""

import os
import sys
import uvicorn
import torchaudio as ta
import traceback
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
import threading
import time

# Global model instance
chatterbox_model = None
model_lock = threading.Lock()

class TTSRequest(BaseModel):
    text: str
    output_path: str = "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions/cloned_output.wav"

class TTSResponse(BaseModel):
    status: str
    message: str
    output_path: str
    generation_time: float

def load_chatterbox_model():
    """Load the ChatterboxTTS model once at startup"""
    global chatterbox_model
    
    try:
        print("🔄 Loading ChatterboxTTS model...")
        start_time = time.time()
        
        from chatterbox.tts import ChatterboxTTS
        chatterbox_model = ChatterboxTTS.from_pretrained(device="cuda")
        
        load_time = time.time() - start_time
        print(f"✅ ChatterboxTTS model loaded successfully in {load_time:.2f} seconds")
        return True
        
    except Exception as e:
        print(f"❌ Failed to load ChatterboxTTS model: {str(e)}")
        print(traceback.format_exc())
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown"""
    print("🚀 Starting ChatterboxTTS Service...")
    
    # Load model at startup
    success = load_chatterbox_model()
    if not success:
        print("❌ Failed to initialize ChatterboxTTS model. Exiting.")
        sys.exit(1)
    
    yield  # App runs here
    
    # Cleanup on shutdown
    print("🛑 Shutting down ChatterboxTTS Service...")

# Create FastAPI app with lifespan events
app = FastAPI(
    title="ChatterboxTTS Service",
    description="Persistent ChatterboxTTS service for fast voice synthesis",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global chatterbox_model
    return {
        "status": "healthy" if chatterbox_model is not None else "unhealthy",
        "model_loaded": chatterbox_model is not None
    }

@app.post("/generate", response_model=TTSResponse)
async def generate_speech(request: TTSRequest):
    """Generate speech using the pre-loaded ChatterboxTTS model"""
    global chatterbox_model
    
    if chatterbox_model is None:
        raise HTTPException(status_code=503, detail="ChatterboxTTS model not loaded")
    
    try:
        start_time = time.time()
        
        # Speaker reference audio path
        speaker_wav_path = "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/chatterbox/priyavoice.m4a"
        
        # Thread-safe model inference
        with model_lock:
            print(f"🔊 Generating speech for: '{request.text[:50]}...'")
            wav = chatterbox_model.generate(request.text, audio_prompt_path=speaker_wav_path)
            ta.save(request.output_path, wav, chatterbox_model.sr)
        
        generation_time = time.time() - start_time
        
        return TTSResponse(
            status="success",
            message="Speech generated successfully",
            output_path=request.output_path,
            generation_time=generation_time
        )
        
    except Exception as e:
        error_msg = f"❌ TTS Generation Error: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/generate_with_custom_output")
async def generate_speech_custom_output(text: str, output_path: str):
    """Generate speech with custom output path"""
    request = TTSRequest(text=text, output_path=output_path)
    return await generate_speech(request)

if __name__ == "__main__":
    print("🎙️ Starting ChatterboxTTS Persistent Service...")
    print("📝 This will keep the model loaded in memory for fast inference")
    print("🔗 Service will be available at http://localhost:8001")
    
    # Run the service
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )