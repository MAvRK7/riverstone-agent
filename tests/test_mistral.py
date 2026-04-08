import os
import asyncio
from dotenv import load_dotenv
from pydantic import BaseModel
from mistralai.client import Mistral

load_dotenv()

# =========================
# Configuration
# =========================
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not MISTRAL_API_KEY:
    raise ValueError("❌ MISTRAL_API_KEY is not set in your .env file")

# Use the best model (change to "mistral-medium-latest" if you want cheaper)
MISTRAL_MODEL = "mistral-large-latest"

# Initialize Mistral V2 client
mistral_client = Mistral(api_key=MISTRAL_API_KEY)

# =========================
# Test Data Model (same as your backend)
# =========================
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
    chat_history: list = []


# =========================
# Test Function
# =========================
async def test_mistral():
    print("🔄 Testing Mistral V2...\n")

    # Sample test cases
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
            additional_info="I work in the CBD and want a short commute"
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
        ),
        CallRequest(
            name="James Wilson",
            phone="+61455551234",
            email="james@example.com",
            message="Hi, can you tell me about Riverstone Place?",
            budget=800000,
            beds=2,
            parking=1,
            timeframe="0-3 months",
            owner_occ=True,
            finance_status="Pre-approved",
            preferred_suburbs=["Abbotsford"],
            additional_info=""
        )
    ]

    for i, call in enumerate(test_cases, 1):
        print(f"{'='*80}")
        print(f"TEST {i}: {call.name} | ${call.budget:,} | {call.beds} bed")
        print(f"Message: {call.message}")
        if call.additional_info:
            print(f"Additional: {call.additional_info}")
        print(f"{'='*80}")

        # Build prompt (same logic as your backend)
        prompt = f"""
You are a friendly Melbourne real estate agent for Harbourline Developments.
Speak naturally, warm, and confident. Max 3-4 sentences.
End with one engaging question.

User said: {call.message}
Budget: ${call.budget:,}
Beds wanted: {call.beds}
Timeframe: {call.timeframe}
Finance: {call.finance_status}
"""

        try:
            chat_response = mistral_client.chat.complete(
                model=MISTRAL_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful, professional real estate sales agent for Harbourline Developments in Melbourne. Speak conversationally like you're on a phone call."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=600
            )

            response_text = chat_response.choices[0].message.content.strip()
            print("✅ Mistral Response:")
            print(response_text)
            print("\n")

        except Exception as e:
            print(f"❌ Mistral Error: {type(e).__name__} - {e}")
            print("\n")

    print("🎉 All tests completed!")


# =========================
# Run the test
# =========================
if __name__ == "__main__":
    asyncio.run(test_mistral())