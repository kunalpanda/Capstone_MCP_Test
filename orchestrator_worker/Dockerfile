FROM python:3.12-slim

WORKDIR /app

# Copy requirements first
COPY orchestrator_worker/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

EXPOSE 8082

CMD ["python", "orchestrator_worker/app.py"]