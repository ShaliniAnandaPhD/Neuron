import io
import os

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

# --- IMPORTANT SIMULATION NOTES ---
# In a real production environment, you would integrate with the actual
# Google Cloud Text-to-Speech API or a specific Gemini API for audio generation.
# This 'MockAudioGen' class is a placeholder to make the backend runnable
# in isolation without needing direct external API credentials for this demo.
# It returns a very short, silent MP3 binary for demonstration purposes.

class MockAudioGen:
    def generate_audio_overview(self, query: str, source_references=None):
        """
        Mocks the audio generation process.
        In a real application, this would involve calling a Google Cloud Text-to-Speech
        API (e.g., from the google-cloud-texttospeech library) or the specific Gemini
        API for audio generation.

        For this demonstration, it returns a minimal valid MP3 byte string.
        This MP3 is essentially silent and very short, serving only to demonstrate
        the file transfer and playback mechanism.
        """
        print(f"MockAudioGen: Simulating audio generation for text: '{query[:50]}...'")


        # A short, silent MP3: MPEG-1 Layer III frames (128 kbps, 44.1 kHz,
        # 417 bytes each) with empty audio data, about a quarter second long.
        # (This used to be a base64 literal, which had been corrupted.)
        frame = b"\xff\xfb\x90\x64" + b"\x00" * 413
        return frame * 10


app = Flask(__name__)
CORS(app)  # the frontend calls the API from another origin (port 80 -> 5000)
audio_generator = MockAudioGen()


@app.post("/api/narrate")
def narrate():
    """Return narration audio (audio/mpeg) for {"text": "..."}."""
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify({"error": "Request body must be JSON with a non-empty 'text'"}), 400

    audio = audio_generator.generate_audio_overview(text)
    return send_file(io.BytesIO(audio), mimetype="audio/mpeg", download_name="narration.mp3")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
