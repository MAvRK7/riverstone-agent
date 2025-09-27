# Riverstone Agent

## Overview

This project implements a voice-enabled AI sales agent for Riverstone Place, a fictional Melbourne apartment development.

The agent qualifies buyers, answers FAQs, handles objections, and books appointments.

It uses the following stack:
- FastAPI for backend API (voice_agent.py)
- Streamlit for frontend UI (app.py)
- Google Gemini for conversational AI (LLM)
- ElevenLabs (primary) and gTTS (fallback) for text-to-speech (voice responses)
- SQLite for lead logging and compliance tracking
- A live demo is available here:
  
👉 https://riverstone-agent-4fz39dbpniix49n5afnfkf.streamlit.app/

Features
- ✔️ Buyer qualification – Based on budget, bedrooms, parking, finance status, timeframe.
- ✔️ FAQ & objection handling – e.g. strata fees, completion timeline, finance, FIRB, rental guarantees.
- ✔️ Appointment booking – 15-minute call or display suite visit using mock API with available slots.
- ✔️ Compliance – Handles “stop/unsubscribe” requests.
- ✔️ Lead logging – Stores call data, booking info, and compliance flags in SQLite.
- ✔️ Voice output – ElevenLabs locally, gTTS fallback (limited on free hosting).


## Setup

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
   DEEPGRAM_API_KEY=your_deepgram_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ELEVENLABS_VOICE_ID=your_voice_id
   BACKEND_URL=https://your-deployed-backend-url/call
   BACKEND_API_KEY=optional_backend_api_key

5. Run the application:
   
   ```bash
   python voice_agent.py

6. Run the Streamlit frontend:

   ```bash
   python -m streamlit run "app.py"

<img width="1205" height="398" alt="image" src="https://github.com/user-attachments/assets/5f916d25-4fa7-445d-81f1-d54b5cecc213" />


## Limitations (Free Demo)

- Phone number / calling not implemented – Twilio/Retell require paid numbers.
- Backend hosting on Render free tier – server idles after ~15 minutes.
- Text-to-Speech – ElevenLabs works locally, but free cloud hosting doesn’t reliably support audio playback.

## Cost & Next Steps

Cost to run ~100 calls: ~$30–50/month (Twilio for calls + persistent hosting + TTS API usage).
If extended, improvements could include:
- Persistent hosting (Render paid / AWS / GCP).
- Fully integrated TTS in the cloud.
- Phone-call support via Twilio or Retell.
- Richer UI/UX with conversation history.
- Integration with Calendly or Google Calendar for real bookings.
  
-------------------------------------------------------------------------------------
✅ This demo was built entirely free of cost to show end-to-end flow, despite limitations.
-------------------------------------------------------------------------------------   

