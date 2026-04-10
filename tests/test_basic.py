import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import your backend
import voice_agent   # assuming this is where app = FastAPI() is

client = TestClient(voice_agent.app)

def test_healthcheck():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_rate_limit_exists():
    """Just check the endpoint doesn't crash"""
    response = client.post("/call", json={
        "name": "Test",
        "phone": "0412345678",
        "email": "test@example.com",
        "message": "Hello",
        "budget": 800000,
        "beds": 2,
        "parking": 1,
        "timeframe": "3-6 months",
        "owner_occ": True,
        "finance_status": "Pre-approved",
        "preferred_suburbs": ["Abbotsford"],
        "additional_info": ""
    })
    assert response.status_code in [200, 422, 429]   # 422 is also acceptable if validation fails