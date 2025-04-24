import os
import sys
import logging
from pathlib import Path
import base64


# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)
from src.auth.factory import create_auth_client


def build_header_token(api_key):
    auth_str = f":{api_key}"
    encoded_bytes = base64.b64encode(auth_str.encode("utf-8"))
    encoded_str = encoded_bytes.decode("utf-8")
    return encoded_str


def authenticate_and_save_lemlist_credentials(user_id):
    logger.info("Starting Lemlist authentication for user %s...", user_id)
    auth_client = create_auth_client()

    api_key = input("Enter Lemlist api key: ").strip()

    if not api_key:
        raise ValueError("API key is required")

    credentials = {
        "client_key": api_key,
        "public_host": "https://api.lemlist.com/api",
    }

    auth_client.save_user_credentials(SERVICE_NAME, user_id, credentials)
    logger.info("Lemlist credentials saved for user %s", user_id)


def get_lemlist_credentials(user_id, api_key=None):
    auth_client = create_auth_client(api_key=api_key)
    credentials = auth_client.get_user_credentials(SERVICE_NAME, user_id)
    api_key = credentials.get("client_key") if credentials else None
    public_host = credentials.get("public_host") if credentials else None
    token = build_header_token(api_key) if api_key else None

    credentials_data = {
        "client_key": api_key,
        "public_host": public_host,
        "token": token,
    }

    if not api_key or not public_host or not token:
        raise ValueError(
            f"Lemlist credentials not found for user {user_id}. Run 'auth' first."
        )

    return credentials_data
