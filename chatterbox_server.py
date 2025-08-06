import os
import sys
import uuid
import torchaudio as ta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from chatterbox.tts import ChatterboxTTS
import traceback
import asyncio
from contextlib import asynccontextmanager

# Global model variable
model = None
log_file = "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions/chatterbox_log.txt"

def log_error(message):
    with open(log_file, "a") as f:
        f.write(message + "\n")

def load_model():
    """Load the ChatterboxTTS model once at startup"""
    global model
    try:
        print("🔄 Loading ChatterboxTTS model...")
        model = ChatterboxTTS.from_pretrained(device="cuda")
        print("✅ ChatterboxTTS model loaded successfully")
    except Exception as e:
        error_msg = f"❌ Failed to load ChatterboxTTS model: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        log_error(error_msg)
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load the model
    load_model()
    yield
    # Shutdown: Cleanup if needed
    global model
    model = None

app = FastAPI(lifespan=lifespan)

class TTSRequest(BaseModel):
    text: str
    output_filename: str = None

@app.post("/synthesize")
async def synthesize_speech(request: TTSRequest):
    """Generate speech using the pre-loaded ChatterboxTTS model"""
    global model
    
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    try:
        # Paths
        speaker_wav_path = "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/chatterbox/priyavoice.m4a"
        
        # Generate unique filename if not provided
        if request.output_filename:
            output_filename = request.output_filename
        else:
            output_filename = f"cloned_output_{uuid.uuid4().hex[:8]}.wav"
        
        output_path = f"/var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions/{output_filename}"
        
        # Generate speech (this should be much faster now)
        wav = model.generate(request.text, audio_prompt_path=speaker_wav_path)
        ta.save(output_path, wav, model.sr)
        
        return {
            "status": "success", 
            "output_path": output_path,
            "filename": output_filename,
            "message": "✅ Synthesized"
        }
        
    except Exception as e:
        err_msg = f"❌ Error in synthesis: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        log_error(err_msg)
        raise HTTPException(status_code=500, detail=err_msg)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global model
    return {
        "status": "healthy" if model is not None else "model_not_loaded",
        "model_loaded": model is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)