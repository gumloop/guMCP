import logging
from src.auth.factory import create_auth_client
import os

logger = logging.getLogger(__name__)


def get_credentials(user_id, api_key=None, service_name=None):
    auth_client = create_auth_client(api_key=api_key)
    credentials = auth_client.get_user_credentials(service_name, user_id)

    # Gumloop environment
    if os.getenv("ENVIRONMENT") == "gumloop":
        credentials = {"client_key": credentials}

    # Get the API key from credentials dictionary
    api_key = credentials.get("client_key") if credentials else None

    credentials_data = {
        "client_key": api_key,
    }

    if not credentials_data["client_key"]:
        raise ValueError(
            f"MailerLite credentials not found for user {user_id}. Run 'auth' first."
        )

    return credentials_data


def authenticate_and_save_credentials(user_id, service_name):
    logger.info("Starting MailerLite authentication for user %s...", user_id)
    auth_client = create_auth_client()

    api_key = input("Enter MailerLite api key: ").strip()

    if not api_key:
        raise ValueError("API key is required")

    credentials = {
        "client_key": api_key,
    }

    auth_client.save_user_credentials(service_name, user_id, credentials)
    logger.info("MailerLite credentials saved for user %s", user_id)
