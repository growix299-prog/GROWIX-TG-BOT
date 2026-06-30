#!/bin/bash

# Port exposed by Hugging Face is 7860
PORT=${PORT:-7860}

echo "Starting FastAPI Backend on port $PORT..."
# Start the FastAPI backend in the background (&)
uvicorn backend.main:app --host 0.0.0.0 --port $PORT &

# Wait a few seconds for backend to start up
sleep 3

# Define custom port for bot health server to avoid port conflicts
export BOT_HEALTH_PORT=8082

echo "Starting Telegram Bot..."
# Start the Telegram Bot in the foreground
python telegram_bot/main.py
