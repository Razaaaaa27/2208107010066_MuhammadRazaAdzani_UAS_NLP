import os
import tempfile
import traceback
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import functions from local modules
from app.stt import transcribe_speech_to_text
from app.llm import generate_response 
from app.tts import transcribe_text_to_speech

app = FastAPI(title="Voice Chat API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/voice-chat")
async def voice_chat(file: UploadFile = File(...)):
    """
    Endpoint untuk layanan voice chat:
    1. Menerima file audio dari pengguna
    2. Transkripsi audio ke teks menggunakan STT
    3. Mengirim teks ke LLM untuk mendapatkan respons
    4. Mengubah respons teks menjadi audio menggunakan TTS
    5. Mengembalikan file audio sebagai respons
    """
    temp_file = None
    try:
        # Baca file audio yang diunggah
        audio_content = await file.read()
        
        # Log for debugging
        print(f"Received audio file: {file.filename}, size: {len(audio_content)} bytes")
        
        # Save audio to temporary file (for debugging)
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"received_audio_{os.path.basename(file.filename)}")
        with open(temp_file, "wb") as f:
            f.write(audio_content)
        print(f"Saved audio to temporary file: {temp_file}")
        
        # Konversi audio ke teks dengan STT
        transcription = transcribe_speech_to_text(audio_content, file_ext=os.path.splitext(file.filename)[1])
        print(f"STT result: {transcription}")
        
        if transcription.startswith("[ERROR]"):
            return JSONResponse(
                status_code=500,
                content={"error": transcription}
            )
        
        # Dapatkan respons dari LLM
        llm_response = generate_response(transcription)
        print(f"LLM response: {llm_response}")
        
        if llm_response.startswith("[ERROR]"):
            return JSONResponse(
                status_code=500,
                content={"error": llm_response}
            )
        
        # Konversi respons teks ke audio dengan TTS
        audio_output_path = transcribe_text_to_speech(llm_response)
        print(f"TTS output path: {audio_output_path}")
        
        if audio_output_path.startswith("[ERROR]"):
            return JSONResponse(
                status_code=500,
                content={"error": audio_output_path}
            )
        
        # Verify the file exists
        if not os.path.exists(audio_output_path):
            return JSONResponse(
                status_code=500,
                content={"error": f"Generated audio file not found at {audio_output_path}"}
            )
            
        file_size = os.path.getsize(audio_output_path)
        print(f"Audio file size: {file_size} bytes")
        
        if file_size == 0:
            return JSONResponse(
                status_code=500,
                content={"error": "Generated audio file is empty"}
            )
        
        # Kembalikan file audio sebagai respons
        return FileResponse(
            path=audio_output_path,
            media_type="audio/wav",
            filename="response.wav"
        )
    
    except Exception as e:
        # Detailed error reporting
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return JSONResponse(
            status_code=500,
            content={"error": error_msg}
        )

@app.get("/health")
async def health_check():
    """Simple endpoint to check if the API is running"""
    # Check dependencies
    health_info = {
        "status": "healthy",
        "components": {}
    }
    
    # Check whisper.cpp directory
    whisper_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "whisper.cpp")
    if os.path.exists(whisper_dir):
        health_info["components"]["whisper.cpp"] = "found"
    else:
        health_info["components"]["whisper.cpp"] = "missing"
        health_info["status"] = "degraded"
    
    # Check coqui_utils directory
    coqui_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "coqui_utils")
    if os.path.exists(coqui_dir):
        health_info["components"]["coqui_utils"] = "found"
    else:
        health_info["components"]["coqui_utils"] = "missing"
        health_info["status"] = "degraded"
    
    # Check if GEMINI_API_KEY is set
    if os.getenv("GEMINI_API_KEY"):
        health_info["components"]["GEMINI_API_KEY"] = "set"
    else:
        health_info["components"]["GEMINI_API_KEY"] = "missing"
        health_info["status"] = "degraded"
    
    return health_info

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)