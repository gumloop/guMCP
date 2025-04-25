import logging
from typing import Dict, List, Any
from src.auth.factory import create_auth_client
from src.utils.oauth.util import (
    run_oauth_flow,
)


logger = logging.getLogger(__name__)

MAILCHIMP_OAUTH_AUTHORIZE_URL = "https://login.mailchimp.com/oauth2/authorize"
MAILCHIMP_OAUTH_TOKEN_URL = "https://login.mailchimp.com/oauth2/token"


def build_mailchimp_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """
    Build the authorization parameters for Mailchimp OAuth.

    Args:
        oauth_config: OAuth configuration dictionary with client_id, redirect_uri, etc.
        redirect_uri: Redirect URI configured for the Mailchimp application.

    Returns:
        Dictionary of query params for the OAuth URL.
    """

    return {
        "response_type": "code",
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
    }


def build_mailchimp_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """
    Build the token request data for Mailchimp OAuth.

    Args:
        oauth_config: OAuth configuration dictionary.
        redirect_uri: Redirect URI used in the flow.
        auth_code: The authorization code returned from Mailchimp.

    Returns:
        Dictionary of data for the token request.
    """
    return {
        "grant_type": "authorization_code",
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "redirect_uri": redirect_uri,
        "code": auth_code,
    }


def build_mailchimp_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Build the headers for the token request to Mailchimp.

    Args:
        oauth_config: OAuth configuration dictionary.

    Returns:
        Dictionary of headers for the token request.
    """
    return {"Content-Type": "application/x-www-form-urlencoded"}


def process_mailchimp_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the token response from Mailchimp.

    Args:
        token_response: Raw token response from Mailchimp.

    Returns:
        Cleaned-up and standardized credentials dictionary.

    Raises:
        ValueError: If response is missing required access token.
    """
    if "error" in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error_description', token_response.get('error', 'Unknown error'))}"
        )

    # Get the access token
    access_token = token_response.get("access_token")
    if not access_token:
        raise ValueError("No access token in response")

    # Make a request to get the server prefix (dc)
    import requests

    metadata_response = requests.get(
        "https://login.mailchimp.com/oauth2/metadata",
        headers={"Authorization": f"OAuth {access_token}"},
    )

    if metadata_response.status_code != 200:
        raise ValueError(f"Failed to get metadata: {metadata_response.text}")

    metadata = metadata_response.json()
    dc = metadata.get("dc")
    if not dc:
        raise ValueError("No server prefix (dc) in metadata response")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "dc": dc,  # Server prefix needed for API calls
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """
    Authenticate and save credentials for Mailchimp.

    Args:
        user_id: ID of the user.
        service_name: Name of the service (Mailchimp).

    Returns:
        Dictionary containing final credentials (e.g., access_token).
    """

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=MAILCHIMP_OAUTH_AUTHORIZE_URL,
        token_url=MAILCHIMP_OAUTH_TOKEN_URL,
        auth_params_builder=build_mailchimp_auth_params,
        token_data_builder=build_mailchimp_token_data,
        token_header_builder=build_mailchimp_token_headers,
        process_token_response=process_mailchimp_token_response,
    )


async def get_credentials(user_id: str, service_name: str) -> str:
    """
    Retrieve (or refresh if needed) the access token for Mailchimp.

    Args:
        user_id: ID of the user.
        service_name: Name of the service (Mailchimp).
        api_key: Optional API key (used by auth client abstraction).

    Returns:
        A valid access token string.
    """

    auth_client = create_auth_client()

    # Get the existing credentials
    credentials = auth_client.get_user_credentials(service_name, user_id)

    if not credentials:
        raise ValueError("No credentials found for Mailchimp")

    return credentials
