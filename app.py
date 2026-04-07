# app.py
import os
import requests
import streamlit as st
from dotenv import load_dotenv
from io import BytesIO
import tempfile
import logging

# Configure logging to output to Streamlit logs
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# For TTS services
from gtts import gTTS
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

# ElevenLabs
try:
    from elevenlabs.client import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

# --------------------------
# Load environment variables
# --------------------------
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "https://riverstone-agent-1.onrender.com/call")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
BACKEND_API_KEY = os.getenv("BACKEND_API_KEY")  # Optional backend auth

st.set_page_config(page_title="Riverstone Voice Agent", layout="centered")
st.title("Riverstone Voice Agent")

# Hero Section
st.markdown("""
    <h2 style='text-align: center; color: #1E3A8A;'>Find Your Perfect Home Across Melbourne</h2>
    <p style='text-align: center; font-size: 1.1em;'>
        Riverstone Place • Harbourview Towers • Yarra Edge • Collingwood Quarter<br>
        <strong>Expert guidance from Harbourline Developments</strong>
    </p>
""", unsafe_allow_html=True)

# Main Property Image 
st.image(
    "hero_image.jpg", 
    use_container_width=True,
    caption="Riverstone Place, Abbotsford — Modern living by the Yarra"
)

# --------------------------
# Prefilled test data
# --------------------------
default_data = {
    "name": "Alex Tran",
    "phone": "+61400000001",
    "email": "alex.tran@example.com",
    "message": "Hi, I want to know about 2-bed apartments.",
    "budget": 900000,
    "beds": 2,
    "parking": 1,
    "timeframe": "3-6 months",
    "owner_occ": True,
    "finance_status": "Pre-approved",
    "preferred_suburbs": "Abbotsford,Riverstone",
    "preferred_slot": "",
    "additional_info": ""
}

# --------------------------
# User Input Form
# --------------------------
with st.form("user_input_form"):
    name = st.text_input("Name", value=default_data["name"])
    phone = st.text_input("Phone", value=default_data["phone"])
    email = st.text_input("Email", value=default_data["email"])
    message = st.text_area("Your question / message", value=default_data["message"])
    budget = st.number_input("Budget (AUD)", min_value=0, value=default_data["budget"])
    beds = st.number_input("Bedrooms", min_value=1, max_value=5, value=default_data["beds"])
    parking = st.number_input("Parking spaces", min_value=0, max_value=3, value=default_data["parking"])
    timeframe = st.selectbox(
        "Timeframe to move",
        ["0-3 months", "3-6 months", "6-12 months", "12+ months"],
        index=["0-3 months", "3-6 months", "6-12 months", "12+ months"].index(default_data["timeframe"])
    )
    owner_occ = st.checkbox("Owner-occupier?", value=default_data["owner_occ"])
    finance_status = st.selectbox(
        "Finance status",
        ["Pre-approved", "In-progress", "Not started"],
        index=["Pre-approved", "In-progress", "Not started"].index(default_data["finance_status"])
    )
    preferred_suburbs = st.text_input("Preferred suburbs (comma-separated)", value=default_data["preferred_suburbs"])
    preferred_slot = st.text_input("Preferred appointment slot (optional ISO datetime)", value=default_data["preferred_slot"])
    additional_info = st.text_area(
        "Anything else we should know? (optional — e.g. must-have features, lifestyle needs, etc.)",
        value="",
        height=80
    )
    submitted = st.form_submit_button("Send")

# --------------------------
# Send request to backend
# --------------------------
if submitted:
    data = {
        "name": name,
        "phone": phone,
        "email": email,
        "message": message,
        "budget": budget,
        "beds": beds,
        "parking": parking,
        "timeframe": timeframe,
        "owner_occ": owner_occ,
        "finance_status": finance_status,
        "preferred_suburbs": [s.strip() for s in preferred_suburbs.split(",") if s.strip()],
        "preferred_slot": preferred_slot,
        "additional_info": additional_info
    }

    with st.spinner("Contacting Riverstone Agent..."):
        try:
            headers = {"Content-Type": "application/json"}
            if BACKEND_API_KEY:
                headers["Authorization"] = f"Bearer {BACKEND_API_KEY}"
            resp = requests.post(BACKEND_URL, json=data, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            if result.get("booking") and result["booking"].get("ok"):
                booking = result["booking"]
                st.subheader("🎉 Booking Confirmed")
                st.markdown(f"**Booking ID:** {booking.get('booking_id')}")
                st.markdown(f"**Slot:** {booking.get('slot')}")
                st.success(booking.get('message'))
            elif result.get("human_handoff"):
                st.success("✅ Great choice! Our sales team will call you within 24 hours to arrange a personal chat.")
            agent_text = result.get("response", "No response from agent.")
        except requests.exceptions.HTTPError as e:
            st.error("Sorry, we couldn’t connect to the agent. Please try again later.")
            logger.error(f"HTTP Error: {e}, Response Text: {resp.text}")
            st.stop()
        except Exception as e:
            st.error("An unexpected error occurred. Please try again later.")
            logger.error(f"Error contacting backend: {e}")
            st.stop()

    st.subheader("Agent Response")
    st.write(agent_text)

    st.divider()
    st.caption("💡 Tip: Ask about specific suburbs (Abbotsford, Richmond, Footscray, Collingwood) or tell us what lifestyle you want — the agent will suggest the best match.")

    # --------------------------
    # Text-to-Speech
    # --------------------------
    tts_played = False

    # Try ElevenLabs first
    if ELEVENLABS_AVAILABLE and ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID:
        try:
            client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
            audio_generator = client.text_to_speech.convert(
                text=agent_text,
                voice_id=ELEVENLABS_VOICE_ID,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )
            audio_buffer = BytesIO()
            for chunk in audio_generator:
                if chunk:
                    audio_buffer.write(chunk)
            audio_buffer.seek(0)
            audio_data = audio_buffer.read()
            if len(audio_data) > 0:
                st.audio(audio_data, format="audio/mp3", autoplay=True)
                tts_played = True
            else:
                raise ValueError("No audio data generated")
        except Exception as e:
            st.warning("Sorry, the premium audio feature is unavailable. Trying basic audio...")
            logger.warning(f"ElevenLabs TTS failed: {e}")

    # Fallback to gTTS
    if not tts_played:
        try:
            tts = gTTS(text=agent_text[:500], lang="en", slow=False)  # 500 char limit is safe
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                tts.save(fp.name)
                st.audio(fp.name, format="audio/mp3", autoplay=True)
                tts_played = True
        except Exception as e:
            logger.warning(f"gTTS failed: {e}")

    # Offline fallback to pyttsx3
    if not tts_played:
        st.warning("🔊 Audio unavailable right now — you can still read the response above.")

