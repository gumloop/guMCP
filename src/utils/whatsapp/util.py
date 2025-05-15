import os
import logging
from src.auth.factory import create_auth_client

logger = logging.getLogger(__name__)


def authenticate_and_save_credentials(user_id: str, service_name: str):
    """Authenticate with Whatsapp and save Access Token, WABA ID, and Phone Number ID"""
    logger.info("Starting Whatsapp authentication for user %s...", user_id)

    # Get auth client
    auth_client = create_auth_client()

    # Prompt user for credentials
    api_key = input("Please enter your WhatsApp Access Token: ").strip()
    waba_id = input("Please enter your WhatsApp Business Account ID: ").strip()
    phone_number_id = input("Please enter your Phone Number ID: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")
    if not waba_id:
        raise ValueError("WABA ID cannot be empty")
    if not phone_number_id:
        raise ValueError("Phone Number ID cannot be empty")

    # Save credentials using auth client
    credentials = {
        "api_key": api_key,
        "waba_id": waba_id,
        "phone_number_id": phone_number_id,
    }
    auth_client.save_user_credentials(service_name, user_id, credentials)

    logger.info(
        "WhatsApp credentials saved for user %s. You can now run the server.", user_id
    )
    return credentials


async def get_credentials(user_id: str, service_name: str, api_key: str = None):
    """Get WhatsApp credentials for the specified user"""
    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials(service_name, user_id)

    def handle_missing_credentials():
        error_str = f"WhatsApp credentials not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logger.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    return credentials_data
