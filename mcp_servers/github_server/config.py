# mcp_servers/github_server/config.py
import os
from dotenv import load_dotenv
from pathlib import Path

# Try to load .env file if it exists (for local development)
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loading .env from {env_path}")
else:
    # Running in Docker/Cloud Run - use environment variables directly
    print("No .env file found - using environment variables")

# Get configuration from environment variables
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN').strip(
) if os.getenv('GITHUB_TOKEN') else None
GITHUB_API_URL = 'https://api.github.com'

# Validate required variables
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable is required")
