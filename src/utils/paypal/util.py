import json
import logging
import requests
import base64
from pathlib import Path


logger = logging.getLogger(__name__)


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> dict:
    """
    Get stored credentials for a user or authenticate if needed.

    Args:
        user_id (str): The user ID to get credentials for
        service_name (str): The service name (e.g., 'paypal')
        api_key (str, optional): Optional API key override

    Returns:
        dict: Token data containing access token and other credentials
    """
    credentials_path = Path(
        f"local_auth/credentials/{service_name}/local_credentials.json"
    )
    with credentials_path.open("r") as f:
        credentials = json.load(f)

    if credentials:
        return credentials

    else:
        raise Exception(f"No valid credentials found for {service_name}")


async def authenticate_and_save_credentials(user_id: str, service_name: str) -> str:
    """
    Authenticate with PayPal and save credentials.

    Args:
        user_id (str): The user ID to authenticate for
        service_name (str): The service name (e.g., 'paypal')

    Returns:
        str: Access token for the service
    """
    config_path = Path(f"local_auth/oauth_configs/{service_name}/oauth.json")
    with config_path.open("r") as f:
        oauth_config = json.load(f)

    client_id = oauth_config["client_id"]
    client_secret = oauth_config["client_secret"]

    # Create base64 encoded credentials
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    # Make request to get access token
    url = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = "grant_type=client_credentials"

    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    token_data = response.json()

    credentials_path = Path(
        f"local_auth/credentials/{service_name}/local_credentials.json"
    )
    credentials_path.parent.mkdir(parents=True, exist_ok=True)

    # Save only the access token
    with open(credentials_path, "w") as f:
        json.dump(token_data, f, indent=2)

    logger.info("PayPal credentials stored successfully")
    return token_data
