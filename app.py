# app.py
import os
import requests
import streamlit as st
from dotenv import load_dotenv
from io import BytesIO
from gtts import gTTS
from elevenlabs.client import ElevenLabs
import tempfile
import logging

# Configure logging to output to Streamlit logs
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# For TTS services
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

# ElevenLabs
try:
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

# --------------------------
# Load environment variables
# --------------------------
load_dotenv()
# Use Streamlit secrets (preferred for deployed version) with fallback
if "api" in st.secrets:
    BACKEND_URL = st.secrets["api"]["BASE_URL"].rstrip("/") + "/call"
else:
    # Fallback for local .env
    BACKEND_URL = os.getenv("BACKEND_URL", "https://riverstone-agent.onrender.com/call")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
BACKEND_API_KEY = os.getenv("BACKEND_API_KEY")  # Optional backend auth

def play_agent_audio(text: str):
    """Helper to play audio - tries ElevenLabs then falls back to gTTS"""
    if not text:
        st.warning("No text to speak.")
        return

    tts_played = False

    # Try ElevenLabs first (premium voice)
    if ELEVENLABS_AVAILABLE and ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID:
        try:
            client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
            audio_generator = client.text_to_speech.convert(
                text=text[:800],
                voice_id=ELEVENLABS_VOICE_ID,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            audio_buffer = BytesIO()
            for chunk in audio_generator:
                if chunk:
                    audio_buffer.write(chunk)
            audio_buffer.seek(0)
            st.audio(audio_buffer, format="audio/mp3")
            tts_played = True
            return
        except Exception as e:
            logger.warning(f"ElevenLabs failed: {e}")

    # Fallback to gTTS (most reliable on Streamlit Cloud)
    try:
        tts = gTTS(text=text[:500], lang="en", slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            st.audio(fp.name, format="audio/mp3")
            tts_played = True
    except Exception as e:
        logger.warning(f"gTTS failed: {e}")

    if not tts_played:
        st.warning("🔊 Audio currently unavailable. Please read the response above.")


st.set_page_config(page_title="Riverstone Voice Agent", layout="centered")
if "follow_up_mode" not in st.session_state:
    st.session_state.follow_up_mode = False
st.title("Riverstone Voice Agent")

# --------------------------
# Hero Section + Main Image
# --------------------------
st.markdown("""
    <h2 style='text-align: center; color: #1E3A8A;'>Find Your Perfect Home Across Melbourne</h2>
    <p style='text-align: center; font-size: 1.1em;'>
        Riverstone Place • Harbourview Towers • Yarra Edge • Collingwood Quarter<br>
        <strong>Expert guidance from Harbourline Developments</strong>
    </p>
""", unsafe_allow_html=True)

# Main Hero Image
st.image(
    "images/hero_img.jpg", 
    use_container_width=True,
    caption="Discover modern living across Melbourne's best inner suburbs"
)

st.markdown("### Our Current Projects")

# Project Cards (beautiful side-by-side)
col1, col2 = st.columns(2)
with col1:
    st.image("images/riverstone.png", use_container_width=True)
    st.markdown("**Riverstone Place** — Abbotsford")
    st.caption("Leafy, riverside living • from $585k")

with col2:
    st.image("images/harbourview.png", use_container_width=True)
    st.markdown("**Harbourview Towers** — Richmond")
    st.caption("Vibrant & central • from $720k")

col3, col4 = st.columns(2)
with col3:
    st.image("images/yarra_edge.png", use_container_width=True)
    st.markdown("**Yarra Edge** — Footscray")
    st.caption("Best value + food scene • from $520k")

with col4:
    st.image("images/collingwood.png", use_container_width=True)
    st.markdown("**Collingwood Quarter** — Collingwood")
    st.caption("Hip & creative • from $635k")

st.divider()

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
            # st.info(f"Debug: Requested {BACKEND_URL} → Status: {resp.status_code}")  # DEBUG !!
            resp.raise_for_status()
            result = resp.json()
            if result.get("booking") and result["booking"].get("ok"):
                booking = result["booking"]
                st.success("✅ Based on your requirements, we've scheduled an appointment with our sales team.")
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


    st.divider()
    st.caption("💡 Tip: Tell us your lifestyle (quiet, vibrant, budget-focused, near parks, etc.) and we’ll suggest the best suburb for you.")
    '''
    # --------------------------
    # Text-to-Speech
    # --------------------------
    st.divider()
    '''
    
    # ====================== AGENT RESPONSE + INTERACTIONS ======================
    st.subheader("Agent Response")
    st.write(agent_text)

    # Voice Button
    if st.button("🔊 Play Agent Response (Voice)"):
        play_agent_audio(agent_text)   # ← We will define this function below

    st.divider()

    # Action Buttons - What next?
    st.markdown("**What would you like to do next?**")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("👍 I'm Happy – Book Meeting", type="primary"):
            st.success("✅ Excellent! Our sales team will contact you shortly to arrange a viewing.")

    with col2:
        if st.button("💬 Ask Follow-up Question"):
            st.session_state.follow_up_mode = True
            st.rerun()

    with col3:
        if st.button("🗣️ Speak to a Human Now"):
            st.success("Our team will call you within 24 hours. Thank you!")

    with col4:
        if st.button("🔄 Start Fresh"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Follow-up Question Input
    if st.session_state.get("follow_up_mode", False):
        follow_up = st.text_input("Your follow-up question:")
        if st.button("Send Follow-up"):
            if follow_up.strip():
                # Reuse the previous form data but update the message
                follow_up_data = data.copy()
                follow_up_data["message"] = follow_up.strip()

                with st.spinner("Asking agent..."):
                    try:
                        headers = {"Content-Type": "application/json"}
                        if BACKEND_API_KEY:
                            headers["Authorization"] = f"Bearer {BACKEND_API_KEY}"

                        resp = requests.post(BACKEND_URL, json=follow_up_data, headers=headers, timeout=30)
                        resp.raise_for_status()
                        new_result = resp.json()
                        new_agent_text = new_result.get("response", "No response.")

                        st.subheader("Agent Follow-up Response")
                        st.write(new_agent_text)

                        # Play audio for follow-up too
                        if st.button("🔊 Play Follow-up Response"):
                            play_agent_audio(new_agent_text)

                    except Exception as e:
                        st.error("Sorry, could not get follow-up response.")
                        logger.error(f"Follow-up error: {e}")
            st.session_state.follow_up_mode = False
            st.rerun()
    # ====================== END OF AGENT RESPONSE SECTION ======================



