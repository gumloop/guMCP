import os
import logging
from src.auth.factory import create_auth_client

logger = logging.getLogger(__name__)


def authenticate_and_save_credentials(user_id: str, service_name: str):
    """Authenticate with Loops and save API Key"""

    auth_client = create_auth_client()
    key = input("Please enter your Loops API key: ").strip()

    if not key:
        raise ValueError("API Key cannot be empty")

    # Save token using auth client
    auth_client.save_user_credentials(service_name, user_id, {"key": key})

    logger.info("Loops API key saved for user %s. You can now run the server.", user_id)
    return key


async def get_credentials(user_id: str, service_name: str, api_key: str = None):
    """Get Loops API key for the specified user"""
    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials(service_name, user_id)

    def handle_missing_credentials():
        error_str = f"Loops API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logger.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    return credentials_data
