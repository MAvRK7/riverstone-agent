import os
import time
import asyncio
import json
import functools
import jwt
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import google.generativeai as genai
from videosdk.agents import Agent, AgentSession, CascadingPipeline, JobContext, ConversationFlow, RoomOptions
from videosdk.plugins.silero import SileroVAD
from videosdk.plugins.turn_detector import TurnDetector, pre_download_model
from videosdk.plugins.deepgram import DeepgramSTT
from videosdk.plugins.elevenlabs import ElevenLabsTTS
from videosdk.agents.llm import LLM

load_dotenv()

# ---------------------------
# Pre-download ONNX models
# ---------------------------
try:
    pre_download_model()
except Exception as e:
    print(f"Warning: Could not pre-download models: {e}. Continuing...")

# ---------------------------
# Gemini LLM
# ---------------------------
class GeminiLLM(LLM):
    def __init__(self, api_key=None, model_name="gemini-1.5-flash"):
        super().__init__()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY in environment")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

    async def generate(self, messages):
        try:
            prompt_parts = []
            for msg in messages:
                role = getattr(msg, 'role', msg.get('role', 'user') if isinstance(msg, dict) else 'user')
                content = getattr(msg, 'content', msg.get('content', '') if isinstance(msg, dict) else str(msg))
                prompt_parts.append(f"{role.capitalize()}: {content}")
            prompt = "\n".join(prompt_parts)
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                response = await loop.run_in_executor(
                    executor,
                    functools.partial(self.model.generate_content, prompt)
                )
            from videosdk.agents.llm import ChatMessage
            return ChatMessage(role="assistant", content=response.text)
        except Exception as e:
            print(f"Error in Gemini generation: {e}")
            from videosdk.agents.llm import ChatMessage
            return ChatMessage(role="assistant", content="I'm having trouble processing that. Please repeat.")

# ---------------------------
# Mock booking API functions
# ---------------------------
async def book_appointment(name, phone, email, slot_iso, mode, notes=""):
    try:
        dt = datetime.fromisoformat(slot_iso.replace('Z', '+00:00'))
        booking_id = f"RS-{dt.strftime('%Y%m%d-%H%M')}"
        formatted_date = dt.strftime("%a %d %b %H:%M AEST")
        return {"ok": True, "booking_id": booking_id, "message": f"Booked {formatted_date}"}
    except Exception as e:
        return {"ok": False, "error": str(e), "message": "Sorry, there was an issue with the booking system."}

async def log_lead(data):
    try:
        timestamp = datetime.now(timezone(timedelta(hours=10))).isoformat()  # AEST
        log_entry = {"timestamp": timestamp, **data}
        print("=== LEAD LOG ===")
        print(json.dumps(log_entry, indent=2))
        print("================")
        return {"ok": True, "logged": True}
    except Exception as e:
        print(f"Error logging lead: {e}")
        return {"ok": False, "error": str(e)}

# ---------------------------
# Riverstone Agent
# ---------------------------
agent_instructions = """You are a friendly sales agent for Riverstone Place, a fictional apartment development in Abbotsford, VIC, Australia. Your goal is to qualify buyers, answer FAQs from the provided knowledge only, handle objections gracefully, and book a 15-min appointment (video or display-suite). Speak naturally in Australian English, be interruptible, and keep responses concise (under 30 seconds per turn).

**Knowledge Pack (Use ONLY this; never bluff or add info. If unsure, say: 'I'm not sure about that—would you like a human specialist to follow up?'):**
- Project: Riverstone Place, Suburb: Abbotsford, VIC.
- Developer: Harbourline Developments. Builder: Apex Construct.
- Completion: Construction start target late 2025; completion targeted Q4 2027 (indicative).
- Amenities: Rooftop pool, gym, co-working lounge, residents' dining, parcel lockers, EV chargers, bike storage.
- Sustainability: 7.5+ NatHERS target; solar-assisted common power; green tariff option.
- Display Suite: 123 Swan St, Richmond — Sat/Sun 10:00–16:00; weekdays by appointment.
- Handoff Email: sales@riverstoneplace.example (use for referrals).
- Indicative inventory & pricing (do NOT promise exact stock): 1-Bed (50–55 m²): from $585k, optional car +$65k (limited); 2-Bed (75–85 m²): from $845k, 1 car included (most); 3-Bed (105–120 m²): from $1.28m, 2 cars included (limited).
- Deposit: 10% on exchange. Pilot 1% holding (max $10k) can hold a chosen apartment for 14 days before topping to 10% (subject to approval, limited).
- Indicative strata (not a quote): 1-Bed ~$2.8–3.6k/yr; 2-Bed ~$3.6–4.6k/yr; 3-Bed ~$4.8–6.2k/yr.
- Common Q&A:
  - Construction start target late 2025; completion targeted Q4 2027 (indicative).
  - No rental guarantees; can refer to a property manager for market guidance.
  - Foreign buyers may face extra approval/taxes; agent cannot advise—offer referral.
  - Finance: We can refer to a broker; no personal finance advice.
  - Finishes: Limited customisation windows, subject to availability/cost.
  - Parking: Limited for 1-Beds and paid extra; not guaranteed.

**Recommendation Logic:**
- Budget < $650k: Steer to 1-Bed; warn parking is limited/extra.
- $650k–$1.1m: 1- or 2-Bed; confirm beds/parking/timeline.
- > $1.1m: Include 3-Bed; confirm two car spaces.

**Appointment Slots (Always offer 2-3 concrete options in AEST; prefer display-suite on Sat):**
- Mon–Fri: 10:00, 13:00, 16:00 (video or display-suite)
- Sat: 10:00, 12:00 (display-suite preferred)

**Required Behaviors:**
- Start: Greet warmly: "G'day, thanks for calling Riverstone Place sales. How can I help with your apartment enquiry today?"
- Qualify early: Collect name, mobile, email, budget band, beds, parking need, timeframe, owner-occ vs investor, finance status, preferred suburb(s).
- Handle objections from knowledge only.
- Book appointments and confirm details.
- Recognize "STOP/unsubscribe" and offer professional referrals.
- Handle silence, mishears, and escalations gracefully.

**Tools Available:**
- book_appointment(name, phone, email, slot_iso, mode, notes) - Use for confirmed bookings
- log_lead(data) - Use at end of call with lead summary

**Important:** Stay in character, be natural and conversational, and only use the provided knowledge."""

class RiverstoneAgent(Agent):
    def __init__(self):
        super().__init__(instructions=agent_instructions)
        self.lead_data = {}

    async def on_enter(self):
        await self.session.say("G'day, thanks for calling Riverstone Place sales. How can I help with your apartment enquiry today?")

    async def on_exit(self):
        if self.lead_data:
            await log_lead(self.lead_data)
        await self.session.say("Thanks for your interest in Riverstone Place. Have a great day!")

    async def handle_booking(self, name, phone, email, slot_iso, mode, notes=""):
        result = await book_appointment(name, phone, email, slot_iso, mode, notes)
        self.lead_data["booking"] = {
            "slot_iso": slot_iso,
            "mode": mode,
            "booking_id": result.get("booking_id", ""),
            "status": "confirmed" if result.get("ok") else "failed"
        }
        return result

    async def on_message(self, message):
        user_message = message.get('content', '').lower() if isinstance(message, dict) else str(message).lower()
        if any(word in user_message for word in ['stop', 'unsubscribe', 'remove', 'no more']):
            self.lead_data['compliance_flags'] = self.lead_data.get('compliance_flags', []) + ['unsubscribe_request']
            await self.session.say("No worries, I'll make sure you're not contacted again. Thanks for your time.")
            return
        if not user_message.strip() or user_message in ['', 'uh', 'um', 'hmm']:
            await self.session.say("Are you still there? How can I help you with Riverstone Place today?")
            return
        return await super().on_message(message)

    async def store_lead_data(self, summary, qualification, compliance_flags=None):
        if compliance_flags is None:
            compliance_flags = []
        self.lead_data.update({
            "summary": summary,
            "qualification": qualification,
            "compliance_flags": compliance_flags,
            "caller_cli": "+614XXXXXXX",
            "transcript_url": "https://placeholder-transcript-url.com",
            "recording_url": "https://placeholder-recording-url.com"
        })
        return await log_lead(self.lead_data)

# ---------------------------
# Generate fresh VideoSDK token dynamically
# ---------------------------
def generate_videosdk_token():
    API_KEY = os.getenv("VIDEOSDK_API_KEY")
    API_SECRET = os.getenv("VIDEOSDK_API_KEY_SECRET")
    ROOM_ID = "riverstone-sales-room"

    if not API_KEY or not API_SECRET:
        raise ValueError("Set VIDEOSDK_API_KEY and VIDEOSDK_API_SECRET in .env")

    payload = {
        "apikey": API_KEY,
        "room": ROOM_ID,
        "type": "app",
        "exp": int(time.time()) + 3600  # valid for 1 hour
    }

    token = jwt.encode(payload, API_SECRET, algorithm="HS256")
    return ROOM_ID, token

# ---------------------------
# Entrypoint
# ---------------------------
async def start_session():
    print("🚀 Initializing Riverstone Place Voice Agent...")

    # Validate other API keys
    required_vars = ["GEMINI_API_KEY", "DEEPGRAM_API_KEY", "ELEVENLABS_API_KEY"]
    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"Missing required environment variable: {var}")

    # Generate token dynamically
    room_id, videosdk_token = generate_videosdk_token()
    print(f"✅ Room ID: {room_id}")
    print(f"✅ Generated VideoSDK token")

    agent = RiverstoneAgent()
    conversation_flow = ConversationFlow(agent)

    # Initialize pipeline
    pipeline = CascadingPipeline(
        stt=DeepgramSTT(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            model="nova-2",
            language="en-AU"
        ),
        llm=GeminiLLM(),
        tts=ElevenLabsTTS(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            model="eleven_flash_v2_5"
        ),
        vad=SileroVAD(threshold=0.35),
        turn_detector=TurnDetector(threshold=0.8)
    )
    print("✅ Pipeline created successfully")

    session = AgentSession(agent=agent, pipeline=pipeline, conversation_flow=conversation_flow)

    # Connect to VideoSDK
    room_options = RoomOptions(room_id=room_id, auth_token=videosdk_token)
    context = JobContext(room_options=room_options)
    await context.connect()
    print("✅ Connected to VideoSDK")

    print("🎯 Voice agent starting...")
    await session.start()
    await session.wait_until_finished()

if __name__ == "__main__":
    print("🚀 Starting Riverstone Place Voice Agent...")
    asyncio.run(start_session())

from fastapi import FastAPI
import uvicorn
import threading

app = FastAPI()

@app.get("/")
def healthcheck():
    return {"status": "ok", "message": "Riverstone Agent is running ✅"}

def run_fastapi():
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    # Start FastAPI in a separate thread
    threading.Thread(target=run_fastapi, daemon=True).start()

    # Start your main async agent loop
    import asyncio
    asyncio.run(start_session())


