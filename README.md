# Riverstone Agent

## Overview

This project implements a voice-enabled AI agent for Riverstone Place.
It uses:
- FastAPI for the backend API (voice_agent.py)
- Streamlit for the frontend (app.py)
- Google Gemini for conversational AI
- ElevenLabs for text-to-speech (voice responses)

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
   
   Note requiremnets for the backend are:

   ```bash
   fastapi==0.115.2  streamlit.30.6
   python-dotenv==1.0.1
   google-generativeai==0.8.3
   PyJWT==2.9.0
   requests==2.31.0
   aiohttp==3.9.5
   websockets==12.0
   deepgram-sdk==3.2.5
   elevenlabs==1.6.0
   streamlit==1.27.0

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
   streamlit run app.py

