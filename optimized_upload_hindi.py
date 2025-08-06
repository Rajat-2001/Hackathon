from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
import uuid
import time
import aiohttp
import asyncio
from datetime import datetime

from app.config import SESSIONS_DIR
from app.pipeline import (
    transcript,
    translator,
    tts,  # Fallback TTS
    audio_quality,
    intent_check,
    corrector
)

router = APIRouter()

# Configuration
CHATTERBOX_SERVER_URL = "http://localhost:8001"
CONNECTION_TIMEOUT = 10  # seconds
REQUEST_TIMEOUT = 30    # seconds

async def generate_indian_accent_audio_optimized(text: str, session_id: str):
    """
    Generate AI audio with Indian accent using optimized HTTP calls
    """
    try:
        start_time = time.time()
        
        # Create unique filename for this session
        filename = f"ai_generated_{uuid.uuid4().hex[:8]}.wav"
        output_path = os.path.join(SESSIONS_DIR, session_id, filename)
        
        # Call the persistent chatterbox server via HTTP
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
            
            async with session.post(f"{CHATTERBOX_SERVER_URL}/synthesize", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Move the generated file to our session directory
                    source_path = result["output_path"]
                    if os.path.exists(source_path):
                        shutil.move(source_path, output_path)
                        
                        elapsed_time = time.time() - start_time
                        print(f"⚡ Indian accent audio generated in {elapsed_time:.2f} seconds")
                        return filename
                    else:
                        raise Exception("Chatterbox server did not generate output file")
                else:
                    error_text = await response.text()
                    raise Exception(f"Chatterbox server error {response.status}: {error_text}")
            
    except aiohttp.ClientError as e:
        raise Exception(f"Failed to connect to chatterbox server: {str(e)}")
    except asyncio.TimeoutError:
        raise Exception("Chatterbox server request timed out")
    except Exception as e:
        raise Exception(f"Error generating Indian accent audio: {str(e)}")

async def fallback_to_regular_tts(text: str, session_id: str):
    """
    Fallback to regular TTS if chatterbox fails
    """
    try:
        # This assumes your regular TTS is synchronous
        ai_audio_path = tts.generate_ai_audio(text, session_id)
        return "ai_generated.wav"  # Standard filename for regular TTS
    except Exception as e:
        raise Exception(f"Fallback TTS also failed: {str(e)}")

@router.post("/")
async def upload_hindi(
    hindi_audio: UploadFile = File(...),
    question: str = Form(...)
):
    try:
        overall_start = time.time()
        
        # 📁 Create session folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"session_{timestamp}"
        session_dir = os.path.join(SESSIONS_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)

        # 📥 Save uploaded audio
        hindi_path = os.path.join(session_dir, "hindi.wav")
        with open(hindi_path, "wb") as f:
            shutil.copyfileobj(hindi_audio.file, f)

        # 🔍 Step 1: Check Audio Quality
        quality = audio_quality.check_audio_quality(hindi_path)

        if quality == "bad":
            return JSONResponse({
                "status": "error",
                "message": "❌ Audio is too short or too silent. Please re-upload a clearer recording."
            })

        elif quality == "repair":
            print("🛠️ Attempting to clean noisy audio...")
            cleaned_path = hindi_path.replace(".wav", "_clean.wav")
            hindi_path = audio_quality.denoise_audio(hindi_path, cleaned_path)

        # 📝 Step 2: Transcribe Hindi
        hindi_text = transcript.generate_transcript(hindi_path)

        # ❓ Step 3: Intent Check — is it relevant to the question?
        intent_result = intent_check.check_hindi_answer_intent(question, hindi_text)
        label = intent_result["relevance"]
        feedback = intent_result["relevance_feedback"]
        suggestions = intent_result["suggestions"]

        if label == "irrelevant":
            return JSONResponse({
                "status": "error",
                "message": "Your response is not relevant to the question. Please re-record.",
                "relevance": "irrelevant",
                "relevance_feedback": {
                    "feedback": feedback,
                    "suggestions": suggestions
                },
                "hindi_transcript": hindi_text
            })

        # 🧠 Step 4: Translate (or correct+translate)
        if label == "restructure":
            english_text = corrector.correct_and_translate(question, hindi_text, correct=True)
        else:
            english_text = corrector.correct_and_translate(question, hindi_text, correct=False)

        # 🔊 Step 5: Generate English AI audio with Indian accent (OPTIMIZED)
        tts_start = time.time()
        try:
            ai_audio_filename = await generate_indian_accent_audio_optimized(english_text, session_id)
            ai_audio_url = f"https://apitranslator.zsapiens.com/sessions/{session_id}/{ai_audio_filename}"
            tts_type = "indian_accent_optimized"
            
            tts_elapsed = time.time() - tts_start
            print(f"🚀 TTS completed in {tts_elapsed:.2f} seconds")
            
        except Exception as audio_error:
            # Fallback to regular TTS if chatterbox fails
            print(f"⚠️ Indian accent TTS failed: {audio_error}")
            print("🔄 Falling back to regular TTS...")
            
            try:
                ai_audio_filename = await fallback_to_regular_tts(english_text, session_id)
                ai_audio_url = f"https://apitranslator.zsapiens.com/sessions/{session_id}/{ai_audio_filename}"
                tts_type = "fallback_regular"
            except Exception as fallback_error:
                raise Exception(f"Both TTS methods failed. Indian accent: {audio_error}, Fallback: {fallback_error}")

        overall_elapsed = time.time() - overall_start
        print(f"🎯 Total processing time: {overall_elapsed:.2f} seconds")

        return JSONResponse({
            "message": "✅ Hindi audio processed successfully",
            "session_id": session_id,
            "hindi_transcript": hindi_text,
            "translated_english": english_text,
            "ai_english_audio_path": ai_audio_url,
            "quality": quality,
            "relevance": label,
            "tts_type": tts_type,
            "processing_time": f"{overall_elapsed:.2f}s"  # Added for monitoring
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))