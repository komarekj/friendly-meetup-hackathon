import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def client_for(role: str) -> tuple[OpenAI, str]:
    """Return (client, model) for the given role, configured from .env."""
    client = OpenAI(
        base_url=os.environ[f"{role}_BASE_URL"],
        api_key=os.environ.get(f"{role}_API_KEY") or "not-needed",
    )
    return client, os.environ[f"{role}_MODEL"]
