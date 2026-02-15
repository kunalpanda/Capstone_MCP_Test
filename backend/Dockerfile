# backend/Dockerfile (Event Gateway)
FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY websocket_server.py .
COPY event_emitter.py .

# Expose WebSocket port
EXPOSE 8000

ENV PORT=8000

# Run the WebSocket server
CMD ["python", "websocket_server.py"]