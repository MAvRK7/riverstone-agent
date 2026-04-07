# test_audio.py - Test audio locally
import os
from dotenv import load_dotenv
from gtts import gTTS
from elevenlabs.client import ElevenLabs
from io import BytesIO
import streamlit as st   # just for testing the component

load_dotenv()

def test_audio(text: str = "Hello, this is a test of the Riverstone Voice Agent. We have great options in Abbotsford and Footscray."):
    print("Testing audio...")

    # Test ElevenLabs
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

    if ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID:
        try:
            client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
            audio_generator = client.text_to_speech.convert(
                text=text[:800],
                voice_id=ELEVENLABS_VOICE_ID,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            buffer = BytesIO()
            for chunk in audio_generator:
                if chunk:
                    buffer.write(chunk)
            buffer.seek(0)
            print("✅ ElevenLabs worked!")
            # To play locally you can save or use playsound, but for now just confirm
            with open("test_elevenlabs.mp3", "wb") as f:
                f.write(buffer.read())
            print("Saved as test_elevenlabs.mp3")
            return
        except Exception as e:
            print(f"ElevenLabs failed: {e}")

    # Fallback gTTS
    try:
        tts = gTTS(text=text[:500], lang="en", slow=False)
        tts.save("test_gtts.mp3")
        print("✅ gTTS worked! Saved as test_gtts.mp3")
    except Exception as e:
        print(f"gTTS failed: {e}")

if __name__ == "__main__":
    test_audio()