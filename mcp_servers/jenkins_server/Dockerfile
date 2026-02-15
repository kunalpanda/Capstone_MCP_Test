# mcp_servers/jenkins_server/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY *.py ./

# Expose MCP port
EXPOSE 8020

ENV PORT=8020

# Run the MCP server
CMD ["python", "server.py"]