import os
import tempfile
import requests
import gradio as gr
import scipy.io.wavfile
from datetime import datetime
import json
import time

# Define color scheme
PRIMARY_COLOR = "#FF5722"  # Orange
SECONDARY_COLOR = "#2196F3"  # Blue
BG_COLOR = "#121212"  # Dark background
TEXT_COLOR = "#FFFFFF"  # White text

# Global chat history
chat_history_list = []

# Helper function to transcribe audio with whisper API
def transcribe_audio(audio_path):
    """Try to transcribe audio using local whisper or other method"""
    try:
        # Use a local Speech-to-Text service or API if available
        # This is a placeholder - implement your preferred method
        
        # Option 1: Send to our FastAPI endpoint
        try:
            with open(audio_path, "rb") as f:
                files = {"file": ("voice.wav", f, "audio/wav")}
                response = requests.post("http://localhost:8000/voice-chat", files=files, timeout=10)
                
                # Get the latest terminal output which should contain the transcription
                terminal_output = get_terminal_output()
                transcript = extract_transcription(terminal_output)
                
                if transcript:
                    return transcript
        except Exception as e:
            print(f"Error using FastAPI for transcription: {str(e)}")
            pass
        
        # If we get here, no transcription is available
        return "Voice message (no transcription available)"
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        return "Voice message (transcription failed)"

# Function to extract transcription from terminal output
def extract_transcription(terminal_output):
    """Extract the transcription text from terminal output"""
    if not terminal_output:
        return None
    
    # Look for "STT result:" in the output
    lines = terminal_output.split('\n')
    for line in lines:
        if line.strip().startswith("STT result:"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                return parts[1].strip()
    
    return None

def voice_chat(audio):
    if audio is None:
        return None, "No audio input detected. Please record audio first.", render_chat([])
    
    sr, audio_data = audio
    
    # Save as .wav
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
        scipy.io.wavfile.write(tmpfile.name, sr, audio_data)
        audio_path = tmpfile.name

    try:
        # First attempt to get terminal output before sending to voice-chat
        # in case we need it for debugging
        current_terminal_output = get_terminal_output()
        
        # Tambahkan parameter language=id pada request API
        with open(audio_path, "rb") as f:
            files = {"file": ("voice.wav", f, "audio/wav")}
            data = {"language": "id"}  # Menambahkan parameter bahasa Indonesia
            response = requests.post("http://localhost:8000/voice-chat", files=files, data=data)
        
        # Wait a moment for logs to be updated
        time.sleep(1.0)
        
        # Get updated terminal output after API call
        terminal_output = get_terminal_output()
        
        # Extract both transcription and LLM response
        transcription = extract_transcription(terminal_output)
        llm_response_text = extract_llm_response(terminal_output)
        
        # Default values if extraction fails
        if not transcription:
            transcription = "Pesan suara (transkrip tidak tersedia)"
        
        if not llm_response_text:
            llm_response_text = "Respons suara (tidak ada teks tersedia)"

        # Create timestamps
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if response.status_code == 200:
            # Save audio response from chatbot
            output_audio_path = os.path.join(tempfile.gettempdir(), "tts_output.wav")
            
            # Write response content to file
            with open(output_audio_path, "wb") as f:
                f.write(response.content)
            
            # Create messages with actual transcription and response text
            user_message = {"role": "user", "time": timestamp, "content": transcription}
            assistant_message = {"role": "assistant", "time": timestamp, "content": llm_response_text}
            
            # Add to history
            chat_history_list.append(user_message)
            chat_history_list.append(assistant_message)
            
            # Write the complete chat history to the log file for debugging
            log_file = os.path.join(tempfile.gettempdir(), "voice_chat_log.txt")
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(f"\nChat history: {chat_history_list}\n")
            
            # Render HTML for chat history
            chat_html = render_chat([])
            
            # Return audio path, status message, and chat HTML
            return output_audio_path, "✅ Response received successfully", chat_html
        else:
            try:
                error_message = response.json().get("error", "Unknown error")
            except:
                error_message = f"Error: {response.status_code} - {response.text[:100]}"
            
            # Add error message to history
            user_message = {"role": "user", "time": timestamp, "content": transcription}
            error_message = {"role": "assistant", "time": timestamp, "content": f"❌ Error: {error_message}"}
            chat_history_list.append(user_message)
            chat_history_list.append(error_message)
            
            chat_html = render_chat([])
            return None, f"❌ Server error: {error_message}", chat_html
    except Exception as e:
        # Add error message to history
        timestamp = datetime.now().strftime("%H:%M:%S")
        user_message = {"role": "user", "time": timestamp, "content": transcription if 'transcription' in locals() else "Pesan suara dikirim (error koneksi)"}
        error_message = {"role": "assistant", "time": timestamp, "content": f"❌ Error: {str(e)}"}
        chat_history_list.append(user_message)
        chat_history_list.append(error_message)
        
        chat_html = render_chat([])
        return None, f"❌ Error connecting to server: {str(e)}", chat_html
    finally:
        # Clean up the temporary file
        if os.path.exists(audio_path):
            os.unlink(audio_path)

# Function to extract LLM response from terminal output
def extract_llm_response(terminal_output):
    """Extract the LLM response text from terminal output"""
    if not terminal_output:
        return None
    
    # Look for "LLM Response:" or "LLM response:" in the output
    lines = terminal_output.split('\n')
    for line in lines:
        if line.strip().startswith("LLM Response:") or line.strip().startswith("LLM response:"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                return parts[1].strip()
    
    return None

# Mock function to represent how you might capture terminal output
def get_terminal_output():
    """Get terminal output from a file or other source"""
    log_file = os.path.join(tempfile.gettempdir(), "voice_chat_log.txt")
    
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                return f.read()
        except:
            pass
    
    return ""

# Chat message display
def render_chat(messages=None):
    """
    Renders chat history as HTML with modern bubble design
    """
    if not chat_history_list:
        return """
        <div class="empty-chat">
            <div class="empty-chat-icon">
                <svg class="wave-icon" viewBox="0 0 24 24" width="100" height="100">
                    <path d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,20a9,9,0,1,1,9-9A9,9,0,0,1,12,21Z" opacity="0.25"></path>
                    <path d="M12,6a1,1,0,0,0-1,1v8a1,1,0,0,0,2,0V7A1,1,0,0,0,12,6Z"></path>
                    <path d="M12,17a1,1,0,1,0,1,1A1,1,0,0,0,12,17Z"></path>
                </svg>
            </div>
            <p>No messages yet. Start a voice conversation!</p>
        </div>
        """
    
    try:
        # Generate HTML for all messages in history
        html = "<div class='chat-container'>"
        
        for msg in chat_history_list:
            # Check if msg is a dictionary with the expected keys
            if not isinstance(msg, dict) or not all(k in msg for k in ["role", "time", "content"]):
                continue
                
            role = msg["role"]
            time = msg["time"]
            content = msg["content"]
            
            if role == "user":
                html += f"""
                <div class='chat-message user-message'>
                    <div class='message-content'>
                        <div class='message-header'>
                            <span class='user-avatar'>
                                <svg viewBox="0 0 24 24" width="24" height="24">
                                    <circle cx="12" cy="7" r="5" fill="#FF5722"></circle>
                                    <path d="M21,24V17c0-3.87-3.13-7-7-7H10c-3.87,0-7,3.13-7,7v7" fill="#FF5722"></path>
                                </svg>
                            </span>
                            <span class='message-sender'>You</span>
                            <span class='message-time'>{time}</span>
                        </div>
                        <div class='message-text'>{content}</div>
                    </div>
                </div>
                """
            else:
                html += f"""
                <div class='chat-message assistant-message'>
                    <div class='message-content'>
                        <div class='message-header'>
                            <span class='assistant-avatar'>
                                <svg viewBox="0 0 24 24" width="24" height="24">
                                    <circle cx="12" cy="12" r="10" fill="#2196F3"></circle>
                                    <path d="M8,12 L11,15 L16,9" stroke="white" stroke-width="2" fill="none"></path>
                                </svg>
                            </span>
                            <span class='message-sender'>Assistant</span>
                            <span class='message-time'>{time}</span>
                        </div>
                        <div class='message-text'>{content}</div>
                    </div>
                </div>
                """
        
        html += "</div>"
        return html
    except Exception as e:
        return f"""
        <div class="error-message">
            <svg viewBox="0 0 24 24" width="24" height="24">
                <circle cx="12" cy="12" r="10" fill="#f44336"></circle>
                <path d="M12,6 L12,14" stroke="white" stroke-width="2"></path>
                <circle cx="12" cy="18" r="1" fill="white"></circle>
            </svg>
            Error displaying chat: {str(e)}
        </div>
        """

def clear_history():
    """Clear chat history and reset UI"""
    global chat_history_list
    chat_history_list = []
    return None, "Cleared. Ready for new message.", render_chat([])

# Custom CSS for styling with animations
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

body {
    background-color: #121212;
    color: #FFFFFF;
    font-family: 'Poppins', sans-serif;
}

.container {
    max-width: 1200px !important;
    margin: 0 auto !important;
}

/* Main header with animation */
.main-header {
    background: linear-gradient(135deg, #FF5722, #FF9800);
    padding: 25px;
    border-radius: 15px;
    margin-bottom: 20px;
    box-shadow: 0 4px 15px rgba(255, 87, 34, 0.3);
    text-align: center;
    position: relative;
    overflow: hidden;
}

.main-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%);
    animation: shimmer 8s infinite linear;
    pointer-events: none;
}

@keyframes shimmer {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}

.logo-animation {
    display: inline-block;
    margin-right: 10px;
    animation: float 3s ease-in-out infinite;
}

@keyframes float {
    0% {
        transform: translateY(0px);
    }
    50% {
        transform: translateY(-10px);
    }
    100% {
        transform: translateY(0px);
    }
}

/* Panels */
.panel {
    background-color: #1E1E1E !important;
    border-radius: 15px !important;
    padding: 20px !important;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
    margin-bottom: 20px !important;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}

.panel:hover {
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4) !important;
    transform: translateY(-3px);
}

.panel::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 3px;
    background: linear-gradient(90deg, #FF5722, #2196F3);
}

/* Audio input panel */
.input-panel h3 {
    display: flex;
    align-items: center;
}

.mic-icon {
    display: inline-block;
    margin-right: 10px;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% {
        transform: scale(1);
        opacity: 1;
    }
    50% {
        transform: scale(1.1);
        opacity: 0.8;
    }
    100% {
        transform: scale(1);
        opacity: 1;
    }
}

.wave-icon {
    animation: wave 2s infinite;
}

@keyframes wave {
    0%, 100% {
        transform: scaleY(1);
    }
    50% {
        transform: scaleY(1.5);
    }
}

/* Buttons */
.btn-record, .btn-submit {
    border-radius: 30px !important;
    padding: 12px 24px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    position: relative;
    overflow: hidden;
    z-index: 1;
}

.btn-submit {
    background-color: #2196F3 !important;
    color: white !important;
    box-shadow: 0 4px 15px rgba(33, 150, 243, 0.4) !important;
}

.btn-submit:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(33, 150, 243, 0.5) !important;
}

.btn-record {
    background-color: #FF5722 !important;
    color: white !important;
    box-shadow: 0 4px 15px rgba(255, 87, 34, 0.4) !important;
}

.btn-record:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(255, 87, 34, 0.5) !important;
}

/* Recording status */
.recording-active {
    color: #FF5722;
    display: flex;
    align-items: center;
    font-weight: 500;
}

.recording-dot {
    display: inline-block;
    width: 12px;
    height: 12px;
    background-color: #FF5722;
    border-radius: 50%;
    margin-right: 8px;
    animation: blink 1s infinite;
}

@keyframes blink {
    0%, 100% {
        opacity: 1;
    }
    50% {
        opacity: 0.3;
    }
}

/* Chat container */
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 15px;
    max-height: 500px;
    overflow-y: auto;
    padding-right: 10px;
    scrollbar-width: thin;
    scrollbar-color: #FF5722 #1E1E1E;
}

.chat-container::-webkit-scrollbar {
    width: 6px;
}

.chat-container::-webkit-scrollbar-track {
    background: #1E1E1E;
}

.chat-container::-webkit-scrollbar-thumb {
    background-color: #FF5722;
    border-radius: 20px;
}

/* Message bubbles */
.chat-message {
    display: flex;
    margin-bottom: 15px;
    animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.user-message {
    justify-content: flex-end;
}

.assistant-message {
    justify-content: flex-start;
}

.message-content {
    max-width: 80%;
    border-radius: 18px;
    padding: 12px 16px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.user-message .message-content {
    background-color: #FF5722;
    border-radius: 18px 18px 0 18px;
}

.assistant-message .message-content {
    background-color: #2196F3;
    border-radius: 18px 18px 18px 0;
}

.message-header {
    display: flex;
    align-items: center;
    margin-bottom: 6px;
}

.user-avatar, .assistant-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    margin-right: 8px;
}

.message-sender {
    font-weight: 600;
    margin-right: 8px;
}

.message-time {
    font-size: 12px;
    opacity: 0.7;
    margin-left: auto;
}

.message-text {
    line-height: 1.4;
}

/* Empty chat state */
.empty-chat {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 0;
    color: rgba(255, 255, 255, 0.6);
    text-align: center;
}

.empty-chat-icon {
    margin-bottom: 20px;
    opacity: 0.6;
}

/* Error message */
.error-message {
    background-color: rgba(244, 67, 54, 0.1);
    border-left: 3px solid #f44336;
    padding: 10px 15px;
    border-radius: 5px;
    display: flex;
    align-items: center;
    gap: 10px;
}

/* Response animation */
.response-animation {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 5px;
    height: 40px;
}

.dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #2196F3;
    animation: dotBounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
    animation-delay: -0.32s;
}

.dot:nth-child(2) {
    animation-delay: -0.16s;
}

@keyframes dotBounce {
    0%, 80%, 100% {
        transform: scale(0);
    }
    40% {
        transform: scale(1);
    }
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .main-header {
        padding: 15px;
    }
    
    .message-content {
        max-width: 90%;
    }
}
"""

# Gradio UI
with gr.Blocks(css=custom_css) as demo:
    # Header with animated icon
    with gr.Row(elem_classes="main-header"):
        gr.HTML("""
        <h1>
            Voice Chatbot AI
        </h1>
        <p>Speak directly to the AI assistant and get voice responses</p>
        """)
    
    # Main content
    with gr.Row():
        # Left column - Input
        with gr.Column(elem_classes="panel input-panel"):
            gr.HTML("""
            <h3>
                <span class="mic-icon">
                    <svg viewBox="0 0 24 24" width="24" height="24">
                        <path fill="#FF5722" d="M12,2C8.7,2,6,4.7,6,8v4c0,3.3,2.7,6,6,6s6-2.7,6-6V8C18,4.7,15.3,2,12,2z M16,12c0,2.2-1.8,4-4,4s-4-1.8-4-4V8c0-2.2,1.8-4,4-4s4,1.8,4,4V12z">
                            <animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite"/>
                        </path>
                        <path fill="#FF5722" d="M12,18c-4.4,0-8,3.6-8,8h2c0-3.3,2.7-6,6-6s6,2.7,6,6h2C20,21.6,16.4,18,12,18z"/>
                    </svg>
                </span>
                Your Message
            </h3>
            """)
            
            audio_input = gr.Audio(
                sources="microphone", 
                type="numpy", 
                label="Record your message"
            )
            
            with gr.Row():
                submit_btn = gr.Button("🔊 Send Voice Message", elem_classes="btn-submit")
                clear_btn = gr.Button("🗑️ Clear", variant="secondary")
            
            # Recording status with animation
            recording_status = gr.HTML("""
            Click the microphone icon to start recording
            """)
            
        # Right column - Output
        with gr.Column(elem_classes="panel"):
            gr.HTML("""
            <h3>
                <span class="mic-icon">
                    <svg viewBox="0 0 24 24" width="24" height="24">
                        <circle cx="12" cy="12" r="10" fill="#2196F3"/>
                        <path d="M9,9 L9,15 L15,12 Z" fill="white">
                            <animateTransform attributeName="transform" type="scale" values="1;1.1;1" dur="2s" repeatCount="indefinite"/>
                        </path>
                    </svg>
                </span>
                AI Response
            </h3>
            """)
            
            audio_output = gr.Audio(
                type="filepath", 
                label="Assistant Reply",
                show_download_button=True
            )
            message_output = gr.HTML("""
            <div style="display: flex; align-items: center; gap: 10px;">
                <svg class="wave-icon" viewBox="0 0 24 24" width="24" height="24">
                    <rect x="2" y="10" width="4" height="10" fill="#2196F3">
                        <animate attributeName="height" values="10;20;10" dur="1s" repeatCount="indefinite"/>
                        <animate attributeName="y" values="10;5;10" dur="1s" repeatCount="indefinite"/>
                    </rect>
                    <rect x="10" y="10" width="4" height="10" fill="#2196F3">
                        <animate attributeName="height" values="10;20;10" dur="1s" begin="0.2s" repeatCount="indefinite"/>
                        <animate attributeName="y" values="10;5;10" dur="1s" begin="0.2s" repeatCount="indefinite"/>
                    </rect>
                    <rect x="18" y="10" width="4" height="10" fill="#2196F3">
                        <animate attributeName="height" values="10;20;10" dur="1s" begin="0.4s" repeatCount="indefinite"/>
                        <animate attributeName="y" values="10;5;10" dur="1s" begin="0.4s" repeatCount="indefinite"/>
                    </rect>
                </svg>
                Waiting for your message...
            </div>
            """)
    
    # Chat history in a modern messaging format
    with gr.Row(elem_classes="panel"):
        gr.HTML("""
        <h3>
            <span class="mic-icon">
                <svg viewBox="0 0 24 24" width="24" height="24">
                    <path fill="#FFFFFF" d="M20,2H4C2.9,2,2,2.9,2,4v18l4-4h14c1.1,0,2-0.9,2-2V4C22,2.9,21.1,2,20,2z M20,16H6l-2,2V4h16V16z">
                        <animate attributeName="opacity" values="0.8;1;0.8" dur="3s" repeatCount="indefinite"/>
                    </path>
                </svg>
            </span>
            Conversation History
        </h3>
        """)
        
        chat_history = gr.HTML(render_chat([]))
    
    # Event handlers
    submit_btn.click(
        fn=voice_chat,
        inputs=audio_input,
        outputs=[audio_output, message_output, chat_history]
    )
    
    clear_btn.click(
        fn=clear_history,
        inputs=None,
        outputs=[audio_output, message_output, chat_history]
    )
    
    # Update recording status with animated indicator
    def update_status(recording):
        if recording:
            return """
            <div class="recording-active">
                <span class="recording-dot"></span>
                Recording in progress... Speak now
            </div>
            """
        else:
            return """
            <div>
                Recording stopped. You can listen to your message or send it.
            </div>
            """
    
    audio_input.change(
        fn=update_status,
        inputs=audio_input,
        outputs=recording_status
    )

# Launch the app with a dark theme
demo.launch(share=False)