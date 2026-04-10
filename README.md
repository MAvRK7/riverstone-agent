# Riverstone Agent

A voice-enabled AI real estate sales agent for **Harbourline Developments** — built to qualify leads, answer property questions, and book appointments for their Melbourne apartment projects.

### Live Demo
👉 [Streamlit Frontend](https://riverstone-agent.streamlit.app)

---

## Overview

This project simulates a conversational AI sales agent for four apartment developments in Melbourne:
- Riverstone Place (Abbotsford)
- Harbourview Towers (Richmond)
- Yarra Edge (Footscray)
- Collingwood Quarter (Collingwood)

The agent can:
- Qualify buyers based on budget, bedrooms, timeframe, and finance status
- Recommend the best matching project
- Handle common questions and objections
- Book mock appointments
- Log leads with compliance tracking

---

## Tech Stack

- **Backend**: FastAPI (`voice_agent.py`)
- **Frontend**: Streamlit (`app.py`)
- **LLM**: Google Gemini (primary) with Mistral fallback
- **Text-to-Speech**: gTTS (frontend) + ElevenLabs (optional)
- **Database**: SQLite (lead logging)
- **Deployment**: Render (backend) + Streamlit Cloud (frontend)

---
  
## Features

- ✅ Intelligent project recommendation based on buyer needs
- ✅ Natural conversation flow with chat history
- ✅ Appointment booking logic with available time slots
- ✅ Compliance handling (stop/unsubscribe requests)
- ✅ Lead logging with qualification data
- ✅ Voice output using gTTS (reliable on cloud)
- ✅ Rate limiting and basic security

---

## Project Structure

mavrk7-riverstone-agent/
├── app.py                    # Streamlit frontend
├── voice_agent.py            # FastAPI backend
├── requirements.txt
├── Dockerfile
├── Procfile
├── .env.example
├── tests/
│   ├── llm_tester.py
│   └── test_mistral.py
└── .github/workflows/        # CI/CD pipelines

---


## Local Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/MAvRK7/riverstone-agent.git
   cd riverstone-agent

2. Create and activate a virtual environment:

    ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
   

4. Create a .env file with the following content:

   ```bash
   GEMINI_API_KEY=your_gemini_api_key
   MISTRAL_API_KEY=your_mistral_key
   BACKEND_URL=https://your-deployed-backend-url/call
   BACKEND_API_KEY=optional_backend_api_key

5. Run the application:
   
   ```bash
   python voice_agent.py

6. Run the Streamlit frontend:

   ```bash
   python -m streamlit run "app.py"

<img width="1205" height="398" alt="image" src="https://github.com/user-attachments/assets/5f916d25-4fa7-445d-81f1-d54b5cecc213" />

---

## Limitations (Free Demo)

- No real phone calling (Twilio/Retell not integrated)
- Backend on Render free tier → sleeps after 15 minutes of inactivity
- Voice input not implemented (planned)
- TTS uses gTTS on frontend for reliability

---

## Cost & Next Steps

Cost to run ~100 calls: ~$30–50/month (Twilio for calls + persistent hosting + TTS API usage).
If extended, improvements could include:
- Persistent hosting (Render paid / AWS / GCP).
- Fully integrated TTS in the cloud.
- Phone-call support via Twilio or Retell.
- Richer UI/UX with conversation history.
- Integration with Calendly or Google Calendar for real bookings.

---

<img width="1440" height="740" alt="image" src="https://github.com/user-attachments/assets/9a543db9-29a6-4048-94aa-bdeabe6b7961" />
Model Output
<img width="1440" height="705" alt="image" src="https://github.com/user-attachments/assets/66b249c7-d47f-4a19-a25e-f6e99fb04d85" />

---
# License

This project is for demonstration purposes. See LICENSE for details.

Made with ❤️ for showcasing AI in real estate sales
---
-------------------------------------------------------------------------------------
✅ This demo was built entirely free of cost to show end-to-end flow, despite limitations.
-------------------------------------------------------------------------------------   

