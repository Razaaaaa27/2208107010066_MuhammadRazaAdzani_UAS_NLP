import os
import tempfile
from google import genai
from google.genai import types
from pydantic import TypeAdapter
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-2.0-flash"

# Ambil API key dari file .env
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

# Verifikasi API key sudah terbaca
if not GOOGLE_API_KEY:
    print("[ERROR] GEMINI_API_KEY tidak ditemukan di file .env")
    # Fallback untuk kebutuhan testing
    GOOGLE_API_KEY = "dummy_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHAT_HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")

# Log file untuk komunikasi dengan Gradio
CHAT_LOG_FILE = os.path.join(tempfile.gettempdir(), "voice_chat_log.txt")

# Prompt sistem yang digunakan untuk membimbing gaya respons LLM
system_instruction = """
You are a responsive, intelligent, and fluent virtual assistant who communicates in Indonesian.
Your task is to provide clear, concise, and informative answers in response to user queries or statements spoken through voice.

Your answers must:
- Be written in polite and easily understandable Indonesian.
- Be short and to the point (maximum 2–3 sentences).
- Avoid repeating the user's question; respond directly with the answer.

Example tone:
User: Cuaca hari ini gimana?
Assistant: Hari ini cuacanya cerah di sebagian besar wilayah, dengan suhu sekitar 30 derajat.

User: Kamu tahu siapa presiden Indonesia?
Assistant: Presiden Indonesia saat ini adalah Joko Widodo.

If you're unsure about an answer, be honest and say that you don't know.
"""

# Inisialisasi klien Gemini dan konfigurasi prompt
client = genai.Client(api_key=GOOGLE_API_KEY)
chat_config = types.GenerateContentConfig(system_instruction=system_instruction)
history_adapter = TypeAdapter(list[types.Content])

# Fungsi untuk menyimpan/memuat riwayat chat
def export_chat_history(chat) -> str:
    return history_adapter.dump_json(chat.get_history()).decode("utf-8")

def save_chat_history(chat):
    try:
        json_history = export_chat_history(chat)
        with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write(json_history)
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan history chat: {e}")

def load_chat_history():
    if not os.path.exists(CHAT_HISTORY_FILE):
        return client.chats.create(model=MODEL, config=chat_config)
    
    if os.path.getsize(CHAT_HISTORY_FILE) == 0:
        return client.chats.create(model=MODEL, config=chat_config)

    with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
        json_str = f.read().strip()

    if not json_str:
        return client.chats.create(model=MODEL, config=chat_config)

    try:
        history = history_adapter.validate_json(json_str)
        return client.chats.create(model=MODEL, config=chat_config, history=history)
    except Exception as e:
        print(f"[ERROR] Gagal load history chat: {e}")
        return client.chats.create(model=MODEL, config=chat_config)

# Inisialisasi sesi chat saat aplikasi dimulai
try:
    chat = load_chat_history()
except Exception as e:
    print(f"[ERROR] Gagal inisialisasi chat: {e}")
    # Fallback untuk kebutuhan testing
    chat = None

# Kirim prompt ke LLM dan kembalikan respons teks
def generate_response(prompt: str) -> str:
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "dummy_key":
        print("[WARNING] Menggunakan respons dummy karena tidak ada GEMINI_API_KEY")
        return "Maaf, saya tidak bisa merespons saat ini karena masalah konfigurasi."
        
    try:
        if chat is None:
            return "[ERROR] Chat belum terinisialisasi"
            
        print(f"Sending to LLM: {prompt}")
        
        # Tambahkan ke log file untuk Gradio
        with open(CHAT_LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"\nSending to LLM: {prompt}\n")
        
        response = chat.send_message(prompt)
        save_chat_history(chat)
        result = response.text.strip()
        
        print(f"LLM Response: {result}")
        
        # Tambahkan respons ke log file untuk Gradio
        with open(CHAT_LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"\nLLM Response: {result}\n")
        
        return result
    except Exception as e:
        print(f"[ERROR] LLM error: {e}")
        return f"[ERROR] {str(e)}"