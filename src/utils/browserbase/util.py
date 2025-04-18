import os
import logging
from src.auth.factory import create_auth_client

logger = logging.getLogger(__name__)


def authenticate_and_save_browserbase_key(user_id: str, service_name: str):
    """Authenticate with Browserbase and save API key"""
    logger.info("Starting Browserbase authentication for user %s...", user_id)

    # Get auth client
    auth_client = create_auth_client()

    # Prompt user for API key if running locally
    api_key = input("Please enter your Browserbase API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")

    project_id = input("Please enter your Browserbase Project ID: ").strip()

    if not project_id:
        raise ValueError("Project key cannot be empty")

    # Save API key using auth client
    auth_client.save_user_credentials(
        service_name, user_id, {"api_key": api_key, "project_id": project_id}
    )

    logger.info(
        "Browserbase API key saved for user %s. You can now run the server.", user_id
    )
    return api_key


async def get_browserbase_credentials(
    user_id: str, service_name: str, api_key: str = None
):
    """Get Browserbase API key for the specified user"""
    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials(service_name, user_id)

    def handle_missing_credentials():
        error_str = f"Browserbase API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logger.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    return credentials_data
