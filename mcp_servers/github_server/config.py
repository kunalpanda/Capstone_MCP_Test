import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loading .env from {env_path}")
else:
    print("No .env file found - using environment variables")

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN').strip(
) if os.getenv('GITHUB_TOKEN') else None
GITHUB_API_URL = 'https://api.github.com'

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable is required")
