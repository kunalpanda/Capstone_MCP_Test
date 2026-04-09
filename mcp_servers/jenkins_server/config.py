import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loading .env from {env_path}")
else:
    print("No .env file found - using environment variables")

JENKINS_URL = os.getenv('JENKINS_URL', 'http://localhost:8080')
JENKINS_USER = os.getenv('JENKINS_USER', 'admin')
JENKINS_TOKEN = os.getenv('JENKINS_TOKEN')

if not JENKINS_TOKEN:
    raise ValueError("JENKINS_TOKEN environment variable is required")
