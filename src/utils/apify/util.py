import os
import logging
from src.auth.factory import create_auth_client

logger = logging.getLogger(__name__)


def authenticate_and_save_credentials(user_id: str, service_name: str):
    """Authenticate with Apify and save API token"""
    logger.info("Starting Apify authentication for user %s...", user_id)

    # Get auth client
    auth_client = create_auth_client()

    # Prompt user for API token
    token = input("Please enter your Apify API token: ").strip()

    if not token:
        raise ValueError("API token cannot be empty")

    # Save token using auth client
    auth_client.save_user_credentials(service_name, user_id, {"token": token})

    logger.info(
        "Apify API token saved for user %s. You can now run the server.", user_id
    )
    return token


async def get_credentials(user_id: str, service_name: str, api_key: str = None):
    """Get Apify API token for the specified user"""
    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials(service_name, user_id)

    if os.getenv("ENVIRONMENT") == "gumloop":
        # Handle credential storage from Gumloop as plain token is returned
        credentials_data = {"token": credentials_data}

    def handle_missing_credentials():
        error_str = f"Apify API token not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logger.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    return credentials_data
