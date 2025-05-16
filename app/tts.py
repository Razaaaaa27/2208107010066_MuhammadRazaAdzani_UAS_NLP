import os
import uuid
import tempfile
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# path ke folder utilitas TTS
COQUI_DIR = os.path.join(BASE_DIR, "coqui_utils")

# Path ke file model TTS
COQUI_MODEL_PATH = os.path.join(COQUI_DIR, "checkpoint_1260000-inference.pth")

# Path ke file konfigurasi
COQUI_CONFIG_PATH = os.path.join(COQUI_DIR, "config.json")

# Nama speaker yang digunakan
COQUI_SPEAKER = "wibowo"

def transcribe_text_to_speech(text: str) -> str:
    """
    Fungsi untuk mengonversi teks menjadi suara menggunakan TTS engine yang ditentukan.
    Args:
        text (str): Teks yang akan diubah menjadi suara.
    Returns:
        str: Path ke file audio hasil konversi.
    """
    path = _tts_with_coqui(text)
    
    # Tambahkan log untuk Gradio
    log_file = os.path.join(tempfile.gettempdir(), "voice_chat_log.txt")
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\nTTS output path: {path}\n")
    
    return path

# === ENGINE 1: Coqui TTS ===
def _tts_with_coqui(text: str) -> str:
    tmp_dir = tempfile.gettempdir()
    output_path = os.path.join(tmp_dir, f"tts_{uuid.uuid4()}.wav")
    
    # Log untuk Gradio
    log_file = os.path.join(tempfile.gettempdir(), "voice_chat_log.txt")
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n > Text: {text}\n")

    # jalankan Coqui TTS dengan subprocess
    cmd = [
        "tts",
        "--text", text,
        "--model_path", COQUI_MODEL_PATH,
        "--config_path", COQUI_CONFIG_PATH,
        "--speaker_idx", COQUI_SPEAKER,
        "--out_path", output_path
    ]
    
    try:
        # Gunakan file log untuk mencatat output TTS
        with open(log_file, "a", encoding="utf-8") as log:
            subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] TTS subprocess failed: {e}")
        return "[ERROR] Failed to synthesize speech"

    return output_path
