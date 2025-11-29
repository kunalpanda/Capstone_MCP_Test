import os
from dotenv import load_dotenv

# Load environment variables from the project root .env
ENV_PATH = os.path.join(os.path.dirname(__file__), "../.env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    print(f"⚠️ .env not found at expected path: {ENV_PATH}")

class Settings:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    JENKINS_TOKEN = os.getenv("JENKINS_TOKEN")
    GITHUB_MCP_URL = os.getenv("GITHUB_MCP_URL", "http://localhost:8010")
    JENKINS_MCP_URL = os.getenv("JENKINS_MCP_URL", "http://localhost:8020")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

settings = Settings()
