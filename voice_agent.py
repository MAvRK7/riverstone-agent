import os
import asyncio
import json
import string
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai


load_dotenv()

# ---------------------------
# CONFIG
# ---------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not GEMINI_API_KEY or not DEEPGRAM_API_KEY or not ELEVENLABS_API_KEY:
    raise ValueError("Set GEMINI_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY in .env")

#new
client = genai.Client(api_key=GEMINI_API_KEY)

# Knowledge pack 
'''
KNOWLEDGE_PACK = {
    "project": "Riverstone Place",
    "suburb": "Abbotsford, VIC",
    "developer": "Harbourline Developments",
    "builder": "Apex Construct",
    "completion_target": "Q4 2027",
    "display_suite": "123 Swan St, Richmond",
    "amenities": [
        "Rooftop pool", "Gym", "Co-working lounge", "Residents’ dining",
        "Parcel lockers", "EV chargers", "Bike storage"
    ],
    "pricing": {
        "1-bed": {"from": 585000, "car": 65000},
        "2-bed": {"from": 845000, "car": "1 included"},
        "3-bed": {"from": 1280000, "car": "2 included"}
    },
    "deposit": "10% on exchange, 1% pilot holding allowed",
    "strata": {
        "1-bed": "2.8–3.6k/yr",
        "2-bed": "3.6–4.6k/yr",
        "3-bed": "4.8–6.2k/yr"
    },
    "handoff_email": "sales@riverstoneplace.example"
}
'''
KNOWLEDGE_PACK = {
    "developer": "Harbourline Developments",
    "projects": [
        {
            "name": "Riverstone Place",
            "suburb": "Abbotsford",
            "price_1bed": "from $585,000",
            "price_2bed": "from $845,000 (1 car included)",
            "price_3bed": "from $1.28m (2 cars included)",
            "strata": "2.8–6.2k/yr",
            "completion": "Q4 2027",
            "lifestyle": "Quiet, leafy, 10 min to CBD, near Yarra River trails"
        },
        {
            "name": "Harbourview Towers",
            "suburb": "Richmond",
            "price_1bed": "from $720,000",
            "price_2bed": "from $1.05m",
            "price_3bed": "from $1.65m",
            "strata": "3.8–7.5k/yr",
            "completion": "Q2 2027",
            "lifestyle": "Vibrant, cafes, shops, 5 min walk to train & MCG"
        },
        {
            "name": "Yarra Edge",
            "suburb": "Footscray",
            "price_1bed": "from $520,000",
            "price_2bed": "from $780,000",
            "price_3bed": "from $1.15m",
            "strata": "2.5–5.1k/yr",
            "completion": "Q3 2026",
            "lifestyle": "Up-and-coming, multicultural food scene, best value, near Footscray Station"
        },
        {
            "name": "Collingwood Quarter",
            "suburb": "Collingwood",
            "price_1bed": "from $635,000",
            "price_2bed": "from $920,000",
            "price_3bed": "from $1.45m",
            "strata": "3.2–6.8k/yr",
            "completion": "Q1 2027",
            "lifestyle": "Hip street art, breweries, trams everywhere, young professional vibe"
        }
    ],
    "handoff_email": "sales@harbourline.com.au",
    "display_suite": "123 Swan St, Richmond"
}

# Appointment slots with ISO datetime
APPOINTMENT_SLOTS = [
    "2025-09-26T10:00:00+10:00", "2025-09-26T13:00:00+10:00", "2025-09-26T16:00:00+10:00",
    "2025-09-27T10:00:00+10:00", "2025-09-27T13:00:00+10:00", "2025-09-27T16:00:00+10:00",
    "2025-09-28T10:00:00+10:00", "2025-09-28T13:00:00+10:00", "2025-09-28T16:00:00+10:00",
    "2025-09-29T10:00:00+10:00", "2025-09-29T13:00:00+10:00", "2025-09-29T16:00:00+10:00",
    "2025-09-30T10:00:00+10:00", "2025-09-30T13:00:00+10:00", "2025-09-30T16:00:00+10:00",
    "2025-10-04T10:00:00+10:00", "2025-10-04T12:00:00+10:00"
]


# ---------------------------
# FastAPI Setup
# ---------------------------
app = FastAPI(title="Riverstone Voice Agent")

# ---------------------------
# Custom Rate Limiter
# ---------------------------
request_log = defaultdict(list)
MAX_REQUESTS = 5       # allowed requests
WINDOW_SECONDS = 60    # in seconds

def check_rate_limit(client_id: str) -> bool:
    now = time.time()
    window_start = now - WINDOW_SECONDS
    request_log[client_id] = [ts for ts in request_log[client_id] if ts > window_start]
    if len(request_log[client_id]) >= MAX_REQUESTS:
        return False
    request_log[client_id].append(now)
    return True

# ---------------------------
# SQLite Logging
# ---------------------------
conn = sqlite3.connect("leads.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    caller_cli TEXT,
    summary TEXT,
    qualification TEXT,
    booking TEXT,
    compliance_flags TEXT,
    transcript_url TEXT,
    recording_url TEXT
)
""")
conn.commit()

async def log_lead(data):
    timestamp = datetime.now(timezone(timedelta(hours=10))).isoformat()
    cursor.execute("""
        INSERT INTO leads (timestamp, caller_cli, summary, qualification, booking, compliance_flags, transcript_url, recording_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        data["caller_cli"],
        data["summary"],
        json.dumps(data["qualification"]),
        json.dumps(data["booking"]),
        json.dumps(data["compliance_flags"]),
        data["transcript_url"],
        data["recording_url"]
    ))
    conn.commit()
    return {"ok": True, "logged": True}

# ---------------------------
# Models
# ---------------------------
class CallRequest(BaseModel):
    name: str
    phone: str
    email: str
    message: str
    budget: int
    beds: int
    parking: int
    timeframe: str
    owner_occ: bool
    finance_status: str
    preferred_suburbs: list
    preferred_slot: str = None
    additional_info: str = ""

# ---------------------------
# Helpers
# ---------------------------
def sanitize_message(msg: str) -> str:
    translator = str.maketrans("", "", string.punctuation)
    return msg.lower().translate(translator).strip()

def iso_to_readable(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str)
    return dt.strftime("%a %d %b %H:%M AEST")

async def book_appointment(name, phone, email, slot_iso, mode="video", notes=""):
    booking_id = f"RS-{datetime.now(timezone(timedelta(hours=10))).strftime('%Y%m%d-%H%M%S')}"
    slot_readable = iso_to_readable(slot_iso) if slot_iso else "N/A"
    return {
        "ok": True,
        "booking_id": booking_id,
        "slot": slot_iso or "N/A",
        "mode": mode,
        "status": "confirmed",
        "message": f"Booked {slot_readable} ({mode})"
    }

# ---------------------------
# LLM Response
# ---------------------------
async def generate_agent_response(call: CallRequest):
    msg = call.message.lower()

    # Quick unsubscribe
    if any(word in msg for word in ["stop", "unsubscribe", "do not call"]):
        return "No worries at all — you won’t be contacted again. Have a great day!"

    # Build smart prompt
    prompt = f"""
You are an experienced, friendly Melbourne real estate sales agent for Harbourline Developments.
Speak like a real person — warm, confident, short sentences, never robotic.
Maximum 3-4 sentences. End with ONE question or clear next step to keep the conversation going.

Our current projects:
- Riverstone Place (Abbotsford): {KNOWLEDGE_PACK['projects'][0]['price_2bed']}, leafy & quiet
- Harbourview Towers (Richmond): {KNOWLEDGE_PACK['projects'][1]['price_2bed']}, vibrant & central
- Yarra Edge (Footscray): {KNOWLEDGE_PACK['projects'][2]['price_2bed']}, best value & food scene
- Collingwood Quarter (Collingwood): {KNOWLEDGE_PACK['projects'][3]['price_2bed']}, hip & creative

User details:
• Name: {call.name}
• Budget: ${call.budget:,}
• Beds wanted: {call.beds}
• Timeframe: {call.timeframe}
• Finance: {call.finance_status}
• Owner-occupier: {call.owner_occ}
• Extra note: {call.message}
• Additional: {getattr(call, 'additional_info', '')}

Based on what they told you, recommend thESe BT matching suburb/project and why it fits them.
If their budget is low → lean Footscray. Medium → Abbotsford/Collingwood. High → Richmond.
Be helpful and slightly salesy. Never push finance/legal advice — refer to {KNOWLEDGE_PACK['handoff_email']}.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",   
        contents=prompt
    )
    return response.text.strip()

# ---------------------------
# Core Endpoint
# ---------------------------
@app.post("/call")
async def handle_call(call: CallRequest, request: Request):
    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests, please try again later."
        )

    msg_clean = sanitize_message(call.message + " " + getattr(call, "additional_info", ""))
    if any(word in msg_clean for word in ["stop", "unsubscribe", "do not call"]):
        return {"response": "No worries at all — you won’t be contacted again. Have a great day!", 
                "compliance_flags": ["unsubscribe_request"]}
    
    # Smart interest scoring for booking / human handoff
    interest_score = 0
    if call.budget >= 800000: interest_score += 2
    if call.beds >= 2: interest_score += 1
    if call.timeframe in ["0-3 months", "3-6 months"]: interest_score += 2
    if any(word in msg_clean for word in ["visit", "see", "appointment", "book", "chat", "meet", "speak", "human"]):
        interest_score += 3

    booking = {"ok": False}
    human_handoff = False

    if interest_score >= 5:  # Hot lead → book appointment
        slot_iso = call.preferred_slot or APPOINTMENT_SLOTS[0]
        mode = "display-suite" if "T10" in slot_iso or "T12" in slot_iso else "video"
        booking = await book_appointment(
            call.name, call.phone, call.email, slot_iso,
            mode=mode,
            notes=f"{call.beds}-bed, ${call.budget}, {call.finance_status}"
        )
    elif interest_score >= 3 and any(word in msg_clean for word in ["human", "speak to someone", "sales team"]):
        human_handoff = True

    # Generate natural response using Gemini
    agent_reply = await generate_agent_response(call)

    # Log lead
    lead_data = {
        "caller_cli": call.phone,
        "summary": f"{call.name}, {call.beds}-bed, budget ${call.budget}, finance {call.finance_status}",
        "qualification": {
            "budget_band": str(call.budget),
            "beds": call.beds,
            "parking": call.parking,
            "owner_occ": call.owner_occ,
            "timeframe": call.timeframe,
            "finance_status": call.finance_status,
            "suburbs": call.preferred_suburbs
        },
        "booking": booking,
        "compliance_flags": [],
        "transcript_url": "https://placeholder-transcript-url.com",
        "recording_url": "https://placeholder-recording-url.com"
    }
    await log_lead(lead_data)

    return {
        "response": agent_reply,
        "booking": booking if booking["ok"] else None,
        "human_handoff": human_handoff,
        "lead_logged": True
    }


# ---------------------------
# Healthcheck
# ---------------------------
@app.get("/")
def healthcheck():
    return {"status": "ok", "message": "Riverstone Agent is running ✅"}

# ---------------------------
# Run via Uvicorn
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
