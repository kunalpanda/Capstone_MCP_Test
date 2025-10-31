import os
import httpx
from dotenv import load_dotenv

# Load environment variables (GITHUB_TOKEN)
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH)

GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("❌ Missing GITHUB_TOKEN in your .env file!")

async def get_repo_info(repo_full_name: str):
    """Fetch detailed GitHub repo info (owner/repo)."""
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    url = f"{GITHUB_API_URL}/repos/{repo_full_name}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

        if response.status_code != 200:
            print(f"❌ GitHub API returned {response.status_code}: {response.text}")
            return None

        data = response.json()
        print("\n📦 Repository Information")
        print("=" * 40)
        print(f"🧾 Name:          {data['name']}")
        print(f"👤 Owner:         {data['owner']['login']}")
        print(f"⭐ Stars:         {data['stargazers_count']}")
        print(f"🍴 Forks:         {data['forks_count']}")
        print(f"📅 Created:       {data['created_at']}")
        print(f"🔄 Updated:       {data['updated_at']}")
        print(f"📝 Description:   {data['description']}")
        print(f"🔗 URL:           {data['html_url']}")
        print("=" * 40)
        return data


async def main():
    print("🔍 GitHub Repository Info Tool")
    repo_name = input("Enter repository (e.g. 'octocat/Hello-World'): ").strip()

    if "/" not in repo_name:
        print("❌ Invalid repo format. Use 'owner/repo'.")
        return

    await get_repo_info(repo_name)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
