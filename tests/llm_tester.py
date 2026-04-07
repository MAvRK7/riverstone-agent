# llm_tester.py
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai   # ✅ new SDK

load_dotenv()

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

# ✅ init client once
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def generate_agent_response(call: CallRequest):
    msg = (call.message + " " + call.additional_info).lower()

    if any(word in msg for word in ["stop", "unsubscribe", "do not call"]):
        return "No worries at all — you won’t be contacted again. Have a great day!"

    prompt = f"""
You are an experienced, friendly Melbourne real estate sales agent for Harbourline Developments.
Speak naturally — warm, confident, short sentences (max 3-4 sentences).
Be helpful and slightly salesy. End with one engaging question.

Our projects:
- Riverstone Place (Abbotsford): from $845k for 2-bed, leafy & riverside
- Harbourview Towers (Richmond): from $1.05m for 2-bed, vibrant central location
- Yarra Edge (Footscray): from $780k for 2-bed, best value + amazing food scene
- Collingwood Quarter (Collingwood): from $920k for 2-bed, hip & creative vibe

User details:
• Name: {call.name}
• Budget: ${call.budget:,}
• Bedrooms: {call.beds}
• Timeframe: {call.timeframe}
• Finance: {call.finance_status}
• Message: {call.message}
• Additional: {call.additional_info}

Recommend the best matching project and why it fits them.
"""

    # ✅ new API call
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )

    return response.text.strip()


async def run_tests():
    test_cases = [
        CallRequest(
            name="Alex Tran",
            phone="+61400000001",
            email="alex@example.com",
            message="I want a 2 bedroom apartment near the city with good transport",
            budget=950000,
            beds=2,
            parking=1,
            timeframe="3-6 months",
            owner_occ=True,
            finance_status="Pre-approved",
            preferred_suburbs=["Abbotsford", "Richmond"],
            additional_info="I work in the CBD and want short commute"
        ),
        CallRequest(
            name="Sarah Chen",
            phone="+61412345678",
            email="sarah@example.com",
            message="Looking for something affordable with good food scene",
            budget=650000,
            beds=2,
            parking=1,
            timeframe="6-12 months",
            owner_occ=True,
            finance_status="In-progress",
            preferred_suburbs=[],
            additional_info="I love markets and multicultural food"
        )
    ]

    for i, call in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i} - Budget ${call.budget} | {call.beds} bed")
        print(f"Message: {call.message}")
        print(f"Additional: {call.additional_info}")
        print(f"{'='*70}")
        
        response = await generate_agent_response(call)
        print(response)
        print("\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_tests())