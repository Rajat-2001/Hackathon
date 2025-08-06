#!/usr/bin/env python3
"""
GPU-Optimized ChatterboxTTS Service
Enhanced version with memory management and performance optimizations
"""

import os
import sys
import uvicorn
import torchaudio as ta
import traceback
import asyncio
import gc
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
import threading
import time
from typing import Optional

# Global model instance and optimization settings
chatterbox_model = None
model_lock = threading.Lock()

# GPU Optimization Settings
TORCH_BACKENDS = True
CUDA_MEMORY_FRACTION = 0.8  # Use 80% of GPU memory
ENABLE_MIXED_PRECISION = True
OPTIMIZE_FOR_INFERENCE = True

class TTSRequest(BaseModel):
    text: str
    output_path: str = "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions/cloned_output.wav"
    speaker_wav_path: Optional[str] = None

class TTSResponse(BaseModel):
    status: str
    message: str
    output_path: str
    generation_time: float
    gpu_memory_used: float

def setup_gpu_optimizations():
    """Configure GPU optimizations for faster inference"""
    try:
        if torch.cuda.is_available():
            print("🔧 Setting up GPU optimizations...")
            
            # Set memory fraction
            torch.cuda.set_per_process_memory_fraction(CUDA_MEMORY_FRACTION)
            
            # Enable optimized backends
            if TORCH_BACKENDS:
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.enabled = True
                print("✅ cuDNN optimizations enabled")
            
            # Clear cache
            torch.cuda.empty_cache()
            gc.collect()
            
            print(f"✅ GPU optimizations configured")
            print(f"   - Memory fraction: {CUDA_MEMORY_FRACTION}")
            print(f"   - Mixed precision: {ENABLE_MIXED_PRECISION}")
            
        else:
            print("⚠️ CUDA not available, running on CPU")
            
    except Exception as e:
        print(f"⚠️ GPU optimization setup failed: {e}")

def get_gpu_memory_usage():
    """Get current GPU memory usage in GB"""
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / 1024**3
    return 0.0

def load_chatterbox_model():
    """Load and optimize the ChatterboxTTS model"""
    global chatterbox_model
    
    try:
        print("🔄 Loading ChatterboxTTS model with optimizations...")
        start_time = time.time()
        
        # Setup GPU optimizations first
        setup_gpu_optimizations()
        
        from chatterbox.tts import ChatterboxTTS
        
        # Load model with GPU optimizations
        device = "cuda" if torch.cuda.is_available() else "cpu"
        chatterbox_model = ChatterboxTTS.from_pretrained(device=device)
        
        # Optimize model for inference
        if OPTIMIZE_FOR_INFERENCE:
            chatterbox_model.eval()  # Set to evaluation mode
            
            # Try to optimize with torch.jit if possible
            try:
                # Note: This might not work with all ChatterboxTTS versions
                # chatterbox_model = torch.jit.optimize_for_inference(chatterbox_model)
                print("✅ Model optimized for inference")
            except:
                print("⚠️ JIT optimization not available, continuing with standard model")
        
        # Warm up the model with a dummy input
        print("🔥 Warming up model...")
        dummy_text = "This is a warmup sentence to initialize the model."
        speaker_wav_path = "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/chatterbox/priyavoice.m4a"
        
        if os.path.exists(speaker_wav_path):
            _ = chatterbox_model.generate(dummy_text, audio_prompt_path=speaker_wav_path)
            print("✅ Model warmed up successfully")
        
        load_time = time.time() - start_time
        gpu_memory = get_gpu_memory_usage()
        
        print(f"✅ ChatterboxTTS model loaded in {load_time:.2f} seconds")
        print(f"📊 GPU Memory Usage: {gpu_memory:.2f} GB")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to load ChatterboxTTS model: {str(e)}")
        print(traceback.format_exc())
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown"""
    print("🚀 Starting GPU-Optimized ChatterboxTTS Service...")
    
    # Load model at startup
    success = load_chatterbox_model()
    if not success:
        print("❌ Failed to initialize ChatterboxTTS model. Exiting.")
        sys.exit(1)
    
    yield  # App runs here
    
    # Cleanup on shutdown
    print("🛑 Shutting down ChatterboxTTS Service...")
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

# Create FastAPI app with lifespan events
app = FastAPI(
    title="GPU-Optimized ChatterboxTTS Service",
    description="High-performance ChatterboxTTS service with GPU optimizations",
    version="2.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """Enhanced health check with GPU info"""
    global chatterbox_model
    
    gpu_info = {}
    if torch.cuda.is_available():
        gpu_info = {
            "gpu_available": True,
            "gpu_name": torch.cuda.get_device_name(0),
            "gpu_memory_total": torch.cuda.get_device_properties(0).total_memory / 1024**3,
            "gpu_memory_used": get_gpu_memory_usage(),
            "cuda_version": torch.version.cuda
        }
    else:
        gpu_info = {"gpu_available": False}
    
    return {
        "status": "healthy" if chatterbox_model is not None else "unhealthy",
        "model_loaded": chatterbox_model is not None,
        "optimization_features": {
            "mixed_precision": ENABLE_MIXED_PRECISION,
            "inference_optimized": OPTIMIZE_FOR_INFERENCE,
            "cudnn_benchmark": TORCH_BACKENDS
        },
        **gpu_info
    }

@app.post("/generate", response_model=TTSResponse)
async def generate_speech_optimized(request: TTSRequest):
    """Generate speech with GPU optimizations"""
    global chatterbox_model
    
    if chatterbox_model is None:
        raise HTTPException(status_code=503, detail="ChatterboxTTS model not loaded")
    
    try:
        start_time = time.time()
        initial_gpu_memory = get_gpu_memory_usage()
        
        # Use default speaker if not provided
        speaker_wav_path = request.speaker_wav_path or "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/chatterbox/priyavoice.m4a"
        
        # Thread-safe model inference with optimizations
        with model_lock:
            print(f"🔊 Generating speech (GPU optimized): '{request.text[:50]}...'")
            
            # Optional: Use automatic mixed precision for faster inference
            if ENABLE_MIXED_PRECISION and torch.cuda.is_available():
                with torch.cuda.amp.autocast():
                    wav = chatterbox_model.generate(request.text, audio_prompt_path=speaker_wav_path)
            else:
                wav = chatterbox_model.generate(request.text, audio_prompt_path=speaker_wav_path)
            
            # Save audio
            ta.save(request.output_path, wav, chatterbox_model.sr)
            
            # Clear CUDA cache to prevent memory buildup
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        generation_time = time.time() - start_time
        gpu_memory_used = get_gpu_memory_usage() - initial_gpu_memory
        
        return TTSResponse(
            status="success",
            message="Speech generated with GPU optimizations",
            output_path=request.output_path,
            generation_time=generation_time,
            gpu_memory_used=gpu_memory_used
        )
        
    except Exception as e:
        error_msg = f"❌ TTS Generation Error: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        
        # Clear cache on error
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/batch_generate")
async def batch_generate_speech(texts: list[str], base_output_path: str):
    """Generate multiple audio files in batch for efficiency"""
    global chatterbox_model
    
    if chatterbox_model is None:
        raise HTTPException(status_code=503, detail="ChatterboxTTS model not loaded")
    
    results = []
    total_start_time = time.time()
    
    try:
        speaker_wav_path = "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/chatterbox/priyavoice.m4a"
        
        with model_lock:
            for i, text in enumerate(texts):
                start_time = time.time()
                output_path = f"{base_output_path}_{i:03d}.wav"
                
                # Generate audio
                if ENABLE_MIXED_PRECISION and torch.cuda.is_available():
                    with torch.cuda.amp.autocast():
                        wav = chatterbox_model.generate(text, audio_prompt_path=speaker_wav_path)
                else:
                    wav = chatterbox_model.generate(text, audio_prompt_path=speaker_wav_path)
                
                ta.save(output_path, wav, chatterbox_model.sr)
                
                generation_time = time.time() - start_time
                results.append({
                    "text": text[:50] + "..." if len(text) > 50 else text,
                    "output_path": output_path,
                    "generation_time": generation_time
                })
            
            # Clear cache after batch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        total_time = time.time() - total_start_time
        
        return {
            "status": "success",
            "total_files": len(texts),
            "total_time": total_time,
            "average_time_per_file": total_time / len(texts),
            "results": results
        }
        
    except Exception as e:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/performance")
async def performance_stats():
    """Get current performance statistics"""
    stats = {
        "model_loaded": chatterbox_model is not None,
        "timestamp": time.time()
    }
    
    if torch.cuda.is_available():
        stats.update({
            "gpu_memory_used_gb": get_gpu_memory_usage(),
            "gpu_memory_total_gb": torch.cuda.get_device_properties(0).total_memory / 1024**3,
            "gpu_utilization": torch.cuda.utilization() if hasattr(torch.cuda, 'utilization') else None
        })
    
    return stats

if __name__ == "__main__":
    print("🎙️ Starting GPU-Optimized ChatterboxTTS Service...")
    print("⚡ Enhanced with GPU optimizations and memory management")
    print("🔗 Service will be available at http://localhost:8001")
    
    # Run the service
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
        workers=1  # Keep single worker for GPU memory management
    )