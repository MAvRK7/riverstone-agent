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
import google.generativeai as genai
from fastapi.responses import JSONResponse

load_dotenv()

# ---------------------------
# CONFIG
# ---------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not GEMINI_API_KEY or not DEEPGRAM_API_KEY or not ELEVENLABS_API_KEY:
    raise ValueError("Set GEMINI_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY in .env")

genai.configure(api_key=GEMINI_API_KEY)

# Knowledge pack from PDF
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
async def generate_agent_response(messages):
    user_msg = ""
    for m in messages:
        if m.get("role") == "user":
            user_msg = sanitize_message(m.get("content", ""))
            break

    if any(word in user_msg for word in ["stop", "unsubscribe"]):
        return "No worries, you will not be contacted again."

    if "strata" in user_msg:
        return f"The indicative strata for apartments ranges from {KNOWLEDGE_PACK['strata']['1-bed']} to {KNOWLEDGE_PACK['strata']['3-bed']} per year. We cannot guarantee exact costs."
    if "completion" in user_msg or "finish" in user_msg:
        return f"Construction is targeted to start in late 2025 and complete by {KNOWLEDGE_PACK['completion_target']} (indicative)."
    if "finance" in user_msg or "loan" in user_msg:
        return f"I’m not able to provide personal finance advice, but we can refer you to a qualified broker via {KNOWLEDGE_PACK['handoff_email']}."
    if "foreign" in user_msg or "firb" in user_msg or "stamp duty" in user_msg:
        return f"Foreign buyers may face extra approvals/taxes; I’m not able to advise, but we can refer you to a specialist via {KNOWLEDGE_PACK['handoff_email']}."
    if "rental guarantee" in user_msg or "yield" in user_msg:
        return "We do not provide rental guarantees. We can refer you to a property manager for market guidance."

    assistant_msg = ""
    for m in messages:
        if m.get("role") == "assistant":
            assistant_msg = m.get("content", "")
            break

    if not assistant_msg.strip():
        return "I’m not sure about that—would you like a human specialist to follow up?"

    return assistant_msg

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

    msg_clean = sanitize_message(call.message)
    if any(word in msg_clean for word in ["stop", "unsubscribe"]):
        return {"response": "No worries, you will not be contacted again.", "compliance_flags": ["unsubscribe_request"]}

    # Qualification & recommendation
    if call.budget < 650000:
        recommendation = "1-bed, parking optional"
    elif 650000 <= call.budget <= 1100000:
        recommendation = "1- or 2-bed, confirm beds/parking/timeline"
    else:
        recommendation = "Include 3-bed, confirm two car spaces"

    # Appointment
    slot_iso = call.preferred_slot or APPOINTMENT_SLOTS[0]
    mode = "display-suite" if "T10" in slot_iso or "T12" in slot_iso else "video"

    booking = await book_appointment(
        call.name, call.phone, call.email, slot_iso,
        mode=mode,
        notes=f"{call.beds}-bed, budget {call.budget}, finance {call.finance_status}"
    )

    # Generate LLM response
    messages = [
        {"role": "system", "content": "You are a Riverstone Place sales agent. Use ONLY the knowledge pack to answer."},
        {"role": "user", "content": call.message},
        {"role": "assistant", "content": f"Based on your budget, I recommend: {recommendation}. Appointment: {booking['message']}"}
    ]
    agent_reply = await generate_agent_response(messages)

    # Log lead
    lead_data = {
        "caller_cli": call.phone,
        "summary": f"{call.name}, {call.beds}-bed, budget {call.budget}, finance {call.finance_status}",
        "qualification": {
            "budget_band": f"{call.budget}",
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

    return {"response": agent_reply, "booking": booking, "lead_logged": True}

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
