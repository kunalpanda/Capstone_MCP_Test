# mcp_servers/github_server/config.py
import os
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "../../.env")
if not os.path.exists(ENV_PATH):
    raise FileNotFoundError(f".env not found at {ENV_PATH}")

print(f"Loading .env from {ENV_PATH}")
load_dotenv(ENV_PATH)

GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN missing in .env file")
