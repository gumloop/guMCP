import logging
from typing import Dict, Any, Optional
from src.auth.factory import create_auth_client

logger = logging.getLogger(__name__)


def authenticate_and_save_credentials(
    user_id: str, service_name: str = None
) -> Dict[str, Any]:
    """
    Prompt the user for Twilio credentials and persist via our auth client.
    """
    logger.info(f"Starting Twilio authentication for user {user_id}...")

    try:
        # Get auth client
        auth_client = create_auth_client()

        # Get credentials from user input
        account_sid = input("Enter your Twilio Account SID: ").strip()
        api_key_sid = input("Enter your Twilio API Key SID: ").strip()
        api_key_secret = input("Enter your Twilio API Key Secret: ").strip()

        # Validate required fields
        if not account_sid or not api_key_sid or not api_key_secret:
            raise ValueError("All credential fields are required")

        # Create credentials dictionary
        creds = {
            "account_sid": account_sid,
            "api_key_sid": api_key_sid,
            "api_key_secret": api_key_secret,
        }

        # Persist via auth client
        auth_client.save_user_credentials(service_name, user_id, creds)
        logger.info(f"Saved Twilio credentials for user {user_id}")
        return creds

    except Exception as e:
        logger.error(f"Error saving Twilio credentials: {e}")
        raise ValueError(f"Failed to save Twilio credentials: {str(e)}")


async def get_credentials(
    user_id: str, service_name: str = None, api_key_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve stored Twilio credentials for a user.
    """
    try:
        # Get auth client
        auth_client = create_auth_client(api_key=api_key_name)

        # Get credentials for this user
        credentials_data = auth_client.get_user_credentials(service_name, user_id)

        if not credentials_data:
            error_str = f"Twilio credentials not found for user {user_id}. Please run authentication first."
            logger.error(error_str)
            raise ValueError(error_str)

        return credentials_data

    except Exception as e:
        logger.error(f"Error retrieving Twilio credentials: {e}")
        raise ValueError(f"Failed to retrieve Twilio credentials: {str(e)}")
