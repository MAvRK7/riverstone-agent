# app.py
import os
import requests
import base64
import streamlit as st
from dotenv import load_dotenv
from gtts import gTTS
from datetime import datetime
import logging

# Configure logging to output to Streamlit logs
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# --------------------------
# Utility Functions
# --------------------------
def iso_to_readable(iso_str):
    """Convert ISO datetime string to a human-readable format."""
    dt = datetime.fromisoformat(iso_str)
    return dt.strftime("%a %d %b %I:%M %p")


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

def play_agent_audio_from_base64(audio_base64: str):
    if not audio_base64:
        st.warning("No audio received")
        return
    try:
        audio_bytes = base64.b64decode(audio_base64)
        st.write(f"🔊 Audio size: {len(audio_bytes)} bytes")  # DEBUG
        st.audio(audio_bytes, format="audio/wav")
    except Exception as e:
        st.error(f"Audio failed: {e}")


st.set_page_config(page_title="Riverstone Voice Agent", layout="centered")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

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
# User Input Form with Voice Button
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
        height=80,
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
        "additional_info": additional_info,
        "chat_history": st.session_state.chat_history,
    }

    with st.spinner("Contacting Riverstone Agent..."):
        try:
            headers = {"Content-Type": "application/json"}
            if BACKEND_API_KEY:
                headers["Authorization"] = f"Bearer {BACKEND_API_KEY}"
            resp = requests.post(BACKEND_URL, json=data, headers=headers, timeout=40)
            resp.raise_for_status()
            result = resp.json()

            #--------------------
            # Save chat history
            #--------------------
            st.session_state.chat_history.append({
                "user": data["message"],
                "agent": result.get("response", "")
            })

            # Store in session state for persistence
            st.session_state.agent_text = result.get("response", "No response from agent.")
            # st.session_state.agent_audio = result.get("audio_base64")
            st.session_state.booking = result.get("booking") if result.get("booking") and result["booking"].get("ok") else None
            st.session_state.last_data = data  # for follow-ups
            st.session_state.follow_up_mode = False  # reset

            # Show booking message immediately
            if st.session_state.booking:
                st.success("✅ Based on your requirements, we've scheduled an appointment with our sales team.")
                st.subheader("🎉 Booking Confirmed")
                st.markdown(f"**Booking ID:** {st.session_state.booking.get('booking_id', 'N/A')}")
                # st.markdown(f"**Slot:** {st.session_state.booking.get('slot', 'N/A')}")
                slot_iso = st.session_state.booking.get('slot')
                if slot_iso:
                    try:
                        readable_slot = iso_to_readable(slot_iso)
                    except Exception as e:
                        logger.warning(f"Failed to parse ISO datetime: {e}")
                        readable_slot = slot_iso  # fallback to raw string
                else:
                    readable_slot = "N/A"
    
                st.markdown(f"**Slot:** {readable_slot}")
                st.success(st.session_state.booking.get('message', 'Appointment booked successfully'))

        except Exception as e:
            error_msg = str(e)
            st.error(f"❌ Backend connection failed: {type(e).__name__}\n\n{error_msg}")
    
            if "timeout" in error_msg.lower():
                st.warning("⏱️ This is likely a cold-start delay on Render Free tier. Try again in 10–20 seconds.")
            elif "connection" in error_msg.lower():
                st.warning("🌐 Could not reach the backend. Check if the URL is correct.")
    
            logger.error(f"Backend request failed: {type(e).__name__} - {error_msg}", exc_info=True)
            st.stop()
        except Exception as e:
            st.error("An unexpected error occurred. Please try again later.")
            logger.error(f"Error contacting backend: {e}")
            st.stop()


# --------------------------
# Show Agent Response + Actions
# --------------------------
if "agent_text" in st.session_state:
    st.divider()
    st.caption("💡 Tip: Tell us your lifestyle (quiet, vibrant, budget-focused, near parks, etc.) and we’ll suggest the best suburb for you.")

    st.subheader("Agent Response")
    st.write(st.session_state.agent_text)

    if st.button("🔊 Play Agent Response (Voice)", key="play_voice"):
        try:
            tts = gTTS(text=st.session_state.agent_text[:300], lang="en")
            tts.save("temp.mp3")

            with open("temp.mp3", "rb") as f:
                audio_bytes = f.read()

            st.audio(audio_bytes, format="audio/mpeg")

        except Exception as e:
            st.error(f"TTS failed: {e}")


    st.divider()

    # Action Buttons
    st.markdown("**What would you like to do next?**")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("👍 I'm Happy – Book Meeting", key="book_meeting"):
            st.success("✅ Excellent! Our sales team will contact you shortly to arrange a viewing.")

    with col2:
        if st.button("💬 Ask Follow-up Question", key="ask_followup"):
            st.session_state.follow_up_mode = True
            st.rerun()

    with col3:
        if st.button("🗣️ Speak to a Human Now", key="speak_human"):
            st.success("Our team will call you within 24 hours. Thank you!")

    with col4:
        if st.button("🔄 Start Fresh", key="start_fresh"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# --------------------------
# Follow-up Input + Response
# --------------------------
if st.session_state.get("follow_up_mode", False):
    if "follow_up_text" not in st.session_state:
        st.session_state.follow_up_text = ""

    st.text_input("Your follow-up question:", key="follow_up_text")

    if st.button("Send Follow-up", key="send_followup"):
        follow_up_text = st.session_state.follow_up_text.strip()
        if follow_up_text and "last_data" in st.session_state:
            follow_up_data = st.session_state.last_data.copy()
            follow_up_data["message"] = follow_up_text
            follow_up_data["chat_history"] = st.session_state.chat_history

            with st.spinner("Asking agent..."):
                try:
                    headers = {"Content-Type": "application/json"}
                    if BACKEND_API_KEY:
                        headers["Authorization"] = f"Bearer {BACKEND_API_KEY}"
                    resp = requests.post(BACKEND_URL, json=follow_up_data, headers=headers, timeout=30)
                    resp.raise_for_status()
                    new_result = resp.json()
                    st.session_state.followup_text = new_result.get("response", "No response.")

                    # Show follow-up response
                    st.subheader("Agent Follow-up Response")
                    st.write(st.session_state.followup_text)



                    # -----------------------
                    # Save follow-up to chat history
                    # -----------------------
                    st.session_state.chat_history.append({
                    "user": follow_up_text,
                    "agent": st.session_state.followup_text
                    })

                    # Reset follow-up mode
                    st.session_state.follow_up_mode = False
                    if "follow_up_text" in st.session_state:
                        del st.session_state.follow_up_text
                    st.rerun()

                except Exception as e:
                    st.error("Sorry, could not get follow-up response.")
                    logger.error(f"Follow-up error: {e}")

        st.session_state.follow_up_mode = False
        if "follow_up_text" in st.session_state:
            del st.session_state.follow_up_text
        st.rerun()