import os

class Settings:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    JENKINS_TOKEN = os.getenv("JENKINS_TOKEN")
    GITHUB_MCP_URL = "http://localhost:8010"
    JENKINS_MCP_URL = "http://localhost:8020"

settings = Settings()
