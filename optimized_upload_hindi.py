from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
import uuid
import httpx
import time
from datetime import datetime

# Assuming these imports work in your environment
# from app.config import SESSIONS_DIR
# from app.pipeline import (
#     transcript,
#     translator,
#     tts,
#     audio_quality,
#     intent_check,
#     corrector
# )

# For demonstration, using placeholder paths
SESSIONS_DIR = "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions"
CHATTERBOX_SERVICE_URL = "http://localhost:8001"

router = APIRouter()

async def generate_indian_accent_audio_optimized(text: str, session_id: str):
    """
    Optimized Indian accent audio generation using persistent ChatterboxTTS service
    """
    try:
        start_time = time.time()
        
        # Create unique filename for this session
        filename = f"ai_generated_{uuid.uuid4().hex[:8]}.wav"
        output_path = os.path.join(SESSIONS_DIR, session_id, filename)
        
        # Check if ChatterboxTTS service is available
        async with httpx.AsyncClient(timeout=5.0) as client:
            health_response = await client.get(f"{CHATTERBOX_SERVICE_URL}/health")
            if health_response.status_code != 200 or not health_response.json().get("model_loaded", False):
                raise Exception("ChatterboxTTS service is not available")
        
        # Generate audio using persistent service
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CHATTERBOX_SERVICE_URL}/generate",
                json={
                    "text": text,
                    "output_path": "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions/cloned_output.wav"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"TTS generation failed: {response.text}")
            
            result = response.json()
        
        # Move the generated file to our session directory with unique name
        default_output = "/var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions/cloned_output.wav"
        
        if os.path.exists(default_output):
            shutil.move(default_output, output_path)
            
            generation_time = time.time() - start_time
            print(f"✅ Indian accent audio generated in {generation_time:.2f} seconds")
            
            return filename
        else:
            raise Exception("ChatterboxTTS did not generate output file")
            
    except httpx.TimeoutException:
        raise Exception("ChatterboxTTS service timeout")
    except httpx.RequestError as e:
        raise Exception(f"Failed to connect to ChatterboxTTS service: {str(e)}")
    except Exception as e:
        raise Exception(f"Error generating Indian accent audio: {str(e)}")

@router.post("/")
async def upload_hindi_optimized(
    hindi_audio: UploadFile = File(...),
    question: str = Form(...)
):
    """Optimized upload_hindi endpoint with persistent ChatterboxTTS service"""
    try:
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
        # quality = audio_quality.check_audio_quality(hindi_path)
        quality = "good"  # Placeholder for demo

        if quality == "bad":
            return JSONResponse({
                "status": "error",
                "message": "❌ Audio is too short or too silent. Please re-upload a clearer recording."
            })

        elif quality == "repair":
            print("🛠️ Attempting to clean noisy audio...")
            # cleaned_path = hindi_path.replace(".wav", "_clean.wav")
            # hindi_path = audio_quality.denoise_audio(hindi_path, cleaned_path)

        # 📝 Step 2: Transcribe Hindi
        # hindi_text = transcript.generate_transcript(hindi_path)
        hindi_text = "प्रदर्शन के लिए हिंदी टेक्स्ट"  # Placeholder

        # ❓ Step 3: Intent Check — is it relevant to the question?
        # intent_result = intent_check.check_hindi_answer_intent(question, hindi_text)
        intent_result = {
            "relevance": "relevant",
            "relevance_feedback": "Good response",
            "suggestions": []
        }  # Placeholder
        
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
        # if label == "restructure":
        #     english_text = corrector.correct_and_translate(question, hindi_text, correct=True)
        # else:
        #     english_text = corrector.correct_and_translate(question, hindi_text, correct=False)
        english_text = "This is the English translation of the Hindi text"  # Placeholder

        # 🔊 Step 5: Generate English AI audio with Indian accent (OPTIMIZED)
        try:
            ai_audio_filename = await generate_indian_accent_audio_optimized(english_text, session_id)
            ai_audio_url = f"https://apitranslator.zsapiens.com/sessions/{session_id}/{ai_audio_filename}"
            tts_type = "indian_accent"
        except Exception as audio_error:
            # Fallback to regular TTS if chatterbox fails
            print(f"⚠️ Indian accent TTS failed: {audio_error}")
            print("🔄 Falling back to regular TTS...")
            # ai_audio_path = tts.generate_ai_audio(english_text, session_id)
            ai_audio_url = f"https://apitranslator.zsapiens.com/sessions/{session_id}/ai_generated.wav"
            tts_type = "fallback"

        return JSONResponse({
            "message": "✅ Hindi audio processed successfully",
            "session_id": session_id,
            "hindi_transcript": hindi_text,
            "translated_english": english_text,
            "ai_english_audio_path": ai_audio_url,
            "quality": quality,
            "relevance": label,
            "tts_type": tts_type
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))