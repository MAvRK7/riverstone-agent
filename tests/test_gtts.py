import os
from io import BytesIO
from gtts import gTTS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_gtts():
    text = "Hello, this is a test from Riverstone Voice Agent. gTTS is working fine."

    print("Starting gTTS test...")
    print(f"Text length: {len(text)} characters")

    try:
        # Create TTS
        tts = gTTS(text=text, lang="en", slow=False)
        print("✅ gTTS object created successfully")
        # Save to file
        tts.save("output.mp3")
        print("✅ Audio saved as output.mp3")

        # Write to memory (no temp file)
        buffer = BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)

        size = len(buffer.getvalue())
        print(f"✅ gTTS audio generated successfully!")
        print(f"Audio size: {size} bytes")

        if size > 1000:
            print("✅ Test PASSED - Audio looks good")
            return True
        else:
            print("⚠️ Test WARNING - Audio file is very small")
            return False

    except Exception as e:
        print(f"❌ gTTS FAILED: {type(e).__name__} - {str(e)}")
        logging.error("gTTS test failed", exc_info=True)
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("gTTS Test for Render Environment")
    print("=" * 60)
    
    success = test_gtts()
    
    if success:
        print("\n🎉 Great! gTTS is working in this environment.")
        print("You can now use it in your main backend.")
    else:
        print("\n💥 gTTS is not working. We need to investigate further.")