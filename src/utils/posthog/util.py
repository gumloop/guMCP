import os
import logging
import requests
from src.auth.factory import create_auth_client

logger = logging.getLogger(__name__)


def get_project_details(api_key: str):
    """Get all projects and their details"""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        org_response = requests.get(
            "https://us.posthog.com/api/organizations/@current/", headers=headers
        )
        org_response.raise_for_status()
        org_data = org_response.json()
        return org_data["teams"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get project details: {str(e)}")
        raise ValueError(f"Failed to get project details: {str(e)}")


def authenticate_and_save_posthog_key(user_id: str, service_name: str):
    """Authenticate with PostHog and save API key"""
    logger.info("Starting PostHog authentication for user %s...", user_id)
    # Get auth client
    auth_client = create_auth_client()

    # Prompt user for API key and host
    api_key = input("Please enter your PostHog API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")

    # Save API key using auth client
    auth_client.save_user_credentials(
        service_name,
        user_id,
        {"api_key": api_key},
    )
    logger.info(
        "PostHog API key saved for user %s. You can now run the server.",
        user_id,
    )
    return api_key


async def get_posthog_credentials(user_id, api_key=None, service_name=None):
    """Get PostHog API key for the specified user"""
    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials(service_name, user_id)

    def handle_missing_credentials():
        error_str = f"PostHog API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logger.error(error_str)
        raise ValueError(error_str)

    if not credentials_data["api_key"]:
        handle_missing_credentials()

    return credentials_data["api_key"]
