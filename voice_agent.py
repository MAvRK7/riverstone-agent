import os
import asyncio
import json
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
import requests

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
        "Rooftop pool",
        "Gym",
        "Co-working lounge",
        "Residents’ dining",
        "Parcel lockers",
        "EV chargers",
        "Bike storage"
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

# Appointment slots (AEST)
APPOINTMENT_SLOTS = [
    "Mon 10:00", "Mon 13:00", "Mon 16:00",
    "Tue 10:00", "Tue 13:00", "Tue 16:00",
    "Wed 10:00", "Wed 13:00", "Wed 16:00",
    "Thu 10:00", "Thu 13:00", "Thu 16:00",
    "Fri 10:00", "Fri 13:00", "Fri 16:00",
    "Sat 10:00", "Sat 12:00"
]

# ---------------------------
# FastAPI Setup
# ---------------------------
app = FastAPI(title="Riverstone Voice Agent")

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
# Booking + Logging
# ---------------------------
async def book_appointment(name, phone, email, slot, mode="video", notes=""):
    # Generate booking_id
    dt = datetime.now(timezone(timedelta(hours=10)))
    booking_id = f"RS-{dt.strftime('%Y%m%d-%H%M%S')}"
    return {
        "ok": True,
        "booking_id": booking_id,
        "message": f"Booked {slot} ({mode})"
    }

async def log_lead(data):
    timestamp = datetime.now(timezone(timedelta(hours=10))).isoformat()
    log_entry = {"timestamp": timestamp, **data}
    print("=== LEAD LOG ===")
    print(json.dumps(log_entry, indent=2))
    print("================")
    return {"ok": True, "logged": True}

# ---------------------------
# LLM Response
# ---------------------------
async def generate_agent_response(messages):
    prompt = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages])
    try:
        response = genai.generate_text(model="gemini-1.5-flash", prompt=prompt)
        return response.text
    except Exception as e:
        return "I'm having trouble processing that. Please repeat."

# ---------------------------
# Core Endpoint
# ---------------------------
@app.post("/call")
async def handle_call(call: CallRequest):
    # Early unsubscribe compliance
    if "stop" in call.message.lower() or "unsubscribe" in call.message.lower():
        return {"response": "No worries, you will not be contacted again.", "compliance_flags": ["unsubscribe_request"]}

    # Qualify user
    recommendation = ""
    if call.budget < 650000:
        recommendation = "1-bed, parking optional"
    elif 650000 <= call.budget <= 1100000:
        recommendation = "1- or 2-bed, confirm beds/parking/timeline"
    else:
        recommendation = "Include 3-bed, confirm two car spaces"

    # Pick appointment slot
    slot = call.preferred_slot or APPOINTMENT_SLOTS[0]

    # Book appointment
    booking = await book_appointment(
        call.name, call.phone, call.email, slot,
        mode="display-suite" if "Sat" in slot else "video",
        notes=f"{call.beds}-bed, budget {call.budget}, finance {call.finance_status}"
    )

    # Generate LLM response
    messages = [
        {"role": "system", "content": "You are a friendly Riverstone Place sales agent."},
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
        "booking": {
            "slot": slot,
            "mode": "display-suite" if "Sat" in slot else "video",
            "booking_id": booking["booking_id"],
            "status": "confirmed" if booking["ok"] else "failed"
        },
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
# Run via Uvicorn for Render
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
