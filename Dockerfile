FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN mkdir -p data chroma_db

# Startup script runs both FastAPI and Streamlit
COPY start.sh .
RUN chmod +x start.sh

EXPOSE 7860

CMD ["./start.sh"]