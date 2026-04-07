FROM python:3.11-slim

# Install system dependencies (for pyttsx3 / espeak)
RUN apt-get update && apt-get install -y \
    espeak \
    libespeak1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose ports
EXPOSE 8501  # Streamlit
EXPOSE 8000  # FastAPI

# Default command: we'll override this per service on Render
CMD ["uvicorn", "voice_agent:app", "--host", "0.0.0.0", "--port", "8000"]