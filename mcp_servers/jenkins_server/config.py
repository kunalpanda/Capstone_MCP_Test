# mcp_servers/jenkins_server/config.py
import os
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "../../.env")
if not os.path.exists(ENV_PATH):
    raise FileNotFoundError(f".env not found at expected path: {ENV_PATH}")

print(f"Loading .env from {ENV_PATH}")
load_dotenv(ENV_PATH)

JENKINS_URL = os.getenv("JENKINS_URL", "http://localhost:8080")
JENKINS_USER = os.getenv("JENKINS_USER")
JENKINS_TOKEN = os.getenv("JENKINS_TOKEN")

if not all([JENKINS_URL, JENKINS_USER, JENKINS_TOKEN]):
    raise ValueError("Missing one or more Jenkins environment variables (URL, USER, TOKEN).")
