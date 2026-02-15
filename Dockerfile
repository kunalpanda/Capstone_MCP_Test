FROM python:3.12-slim

WORKDIR /app

# Copy requirements first
COPY orchestrator_worker/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project (orchestrator, backend, prompts, orchestrator_worker)
COPY orchestrator/ ./orchestrator/
COPY backend/ ./backend/
COPY prompts/ ./prompts/
COPY orchestrator_worker/ ./orchestrator_worker/

EXPOSE 8082

# Run the orchestrator worker
CMD ["python", "-m", "orchestrator_worker.app"]