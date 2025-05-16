import os
import uuid
import tempfile
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# path ke folder utilitas STT
WHISPER_DIR = os.path.join(BASE_DIR, "whisper.cpp")

# Path ke binary whisper-cli
WHISPER_BINARY = os.path.join(WHISPER_DIR, "build", "bin", "Release", "whisper-cli.exe")

# Path ke file model Whisper
WHISPER_MODEL_PATH = os.path.join(WHISPER_DIR, "models", "ggml-large-v3-turbo.bin")

def transcribe_speech_to_text(file_bytes: bytes, file_ext: str = ".wav") -> str:
    """
    Transkrip file audio menggunakan whisper.cpp CLI
    Args:
        file_bytes (bytes): Isi file audio
        file_ext (str): Ekstensi file, default ".wav"
    Returns:
        str: Teks hasil transkripsi
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, f"{uuid.uuid4()}{file_ext}")
        result_path = os.path.join(tmpdir, "transcription.txt")

        # simpan audio ke file temporer
        with open(audio_path, "wb") as f:
            f.write(file_bytes)

        # jalankan whisper.cpp dengan subprocess
        # Penting: tambahkan parameter -l id untuk bahasa Indonesia
        cmd = [
            WHISPER_BINARY,
            "-m", WHISPER_MODEL_PATH,
            "-f", audio_path,
            "-l", "id",  # Menentukan bahasa Indonesia
            "-otxt",
            "-of", os.path.join(tmpdir, "transcription")
        ]

        try:
            # Save the input audio file path to the log file
            log_file = os.path.join(tempfile.gettempdir(), "voice_chat_log.txt")
            with open(log_file, "w", encoding="utf-8") as log:
                log.write(f"Processing audio file: {audio_path}\n")
                log.write(f"Language setting: Indonesian (-l id)\n")
                subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            return f"[ERROR] Whisper failed: {e}"
        
        # baca hasil transkripsi
        try:
            with open(result_path, "r", encoding="utf-8") as result_file:
                transcription = result_file.read()
                
                # Append the transcription to the log file
                with open(log_file, "a", encoding="utf-8") as log:
                    log.write(f"STT result: {transcription}\n")
                
                return transcription
        except FileNotFoundError:
            return "[ERROR] Transcription file not found"