# app.py
import os
import requests
import streamlit as st
from dotenv import load_dotenv
from io import BytesIO
from gtts import gTTS

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
    "preferred_slot": ""
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
        "preferred_suburbs": [s.strip() for s in preferred_suburbs.split(",")],
        "preferred_slot": preferred_slot
    }

    with st.spinner("Contacting Riverstone Agent..."):
        try:
            headers = {"Content-Type": "application/json"}
            if BACKEND_API_KEY:
                headers["Authorization"] = f"Bearer {BACKEND_API_KEY}"
            resp = requests.post(BACKEND_URL, json=data, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            agent_text = result.get("response", "No response from agent.")
        except requests.exceptions.HTTPError as e:
            st.error(f"HTTP Error: {e}")
            st.error(f"Response Text: {resp.text}")
            st.stop()
        except Exception as e:
            st.error(f"Error contacting backend: {e}")
            st.stop()

    st.subheader("Agent Response")
    st.write(agent_text)

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
                model_id="eleven_multilingual_v2"
            )
            audio_buffer = BytesIO()
            for chunk in audio_generator:
                audio_buffer.write(chunk)
            audio_buffer.seek(0)
            st.audio(audio_buffer.read(), format="audio/mp3")
            tts_played = True
        except Exception as e:
            st.warning(f"ElevenLabs TTS failed: {e}")

    # Fallback to gTTS
    if not tts_played:
        try:
            tts = gTTS(text=agent_text, lang="en")
            audio_buffer = BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            st.audio(audio_buffer.read(), format="audio/mp3")
        except Exception as e:
            st.error(f"gTTS TTS failed: {e}")

    # --------------------------
    # Display booking info
    # --------------------------
    if "booking" in result:
        booking = result["booking"]
        st.subheader("Booking Confirmation")
        st.markdown(f"**Booking ID:** {booking.get('booking_id', 'N/A')}")
        st.markdown(f"**Slot:** {booking.get('slot', 'N/A')}")
        st.markdown(f"**Mode:** {booking.get('mode', 'N/A')}")
        st.markdown(f"**Status:** {booking.get('status', 'N/A')}")
        st.markdown(f"**Message:** {booking.get('message', 'N/A')}")
