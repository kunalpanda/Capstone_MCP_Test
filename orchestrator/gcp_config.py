import os
from google.cloud import secretmanager
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "../.env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
    print("📁 Loaded .env for local development")


def get_secret(secret_id: str, project_id: str = None) -> str:
    """Try env var first (local dev), fall back to Secret Manager (production)."""
    env_var_name = secret_id.upper().replace('-', '_')
    env_value = os.getenv(env_var_name)

    if env_value:
        print(f"🔑 Using {secret_id} from environment variable")
        return env_value

    try:
        if not project_id:
            project_id = os.getenv('PROJECT_ID') or os.getenv('GCP_PROJECT')

        if not project_id:
            raise ValueError(
                "PROJECT_ID not set - cannot access Secret Manager")

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})

        print(f"🔑 Using {secret_id} from Secret Manager")
        return response.payload.data.decode('UTF-8')

    except Exception as e:
        print(f"❌ Failed to get secret {secret_id}: {e}")
        raise


def get_client_secrets(client_id: str, project_id: str = None) -> dict:
    if not project_id:
        project_id = os.getenv('PROJECT_ID', 'capstone-cicd-ai')

    print(f"🔑 Fetching secrets for client_id='{client_id}'")

    return {
        'github_token':   get_secret(f'client-{client_id}-github-token',  project_id),
        'jenkins_token':  get_secret(f'client-{client_id}-jenkins-token', project_id),
        'jenkins_url':    get_secret(f'client-{client_id}-jenkins-url',   project_id),
        'jenkins_user':   get_secret(f'client-{client_id}-jenkins-user',  project_id),
    }


class Settings:

    def __init__(self):
        self.PROJECT_ID = os.getenv('PROJECT_ID', 'capstone-cicd-ai')
        self.REGION = os.getenv('REGION', 'us-central1')

        self.GITHUB_TOKEN = get_secret('github-token', self.PROJECT_ID)
        self.ANTHROPIC_API_KEY = get_secret(
            'anthropic-api-key', self.PROJECT_ID)
        self.JENKINS_TOKEN = get_secret('jenkins-token', self.PROJECT_ID)

        self.GITHUB_MCP_URL = os.getenv(
            'GITHUB_MCP_URL', 'http://localhost:8010')
        self.JENKINS_MCP_URL = os.getenv(
            'JENKINS_MCP_URL', 'http://localhost:8020')

        self.PUBSUB_TOPIC_COMMANDS = os.getenv(
            'PUBSUB_TOPIC_COMMANDS', 'workflow-commands')
        self.PUBSUB_TOPIC_EVENTS = os.getenv(
            'PUBSUB_TOPIC_EVENTS', 'workflow-events')

        self.TARGET_LINE_COVERAGE = int(
            os.getenv('TARGET_LINE_COVERAGE', '75'))
        self.TARGET_BRANCH_COVERAGE = int(
            os.getenv('TARGET_BRANCH_COVERAGE', '70'))
        self.TARGET_METHOD_COVERAGE = int(
            os.getenv('TARGET_METHOD_COVERAGE', '75'))

        self.DEV_MODE = os.getenv('DEV_MODE', 'true').lower() == 'true'

        print(f"⚙️  Configuration loaded (DEV_MODE={self.DEV_MODE})")


settings = Settings()
