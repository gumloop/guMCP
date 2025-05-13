import base64
import logging
from typing import Dict, List, Any

from src.utils.oauth.util import (
    run_oauth_flow,
    refresh_token_if_needed,
)


logger = logging.getLogger(__name__)

DROPBOX_OAUTH_AUTHORIZE_URL = "https://www.dropbox.com/oauth2/authorize"
DROPBOX_OAUTH_TOKEN_URL = "https://api.dropbox.com/oauth2/token"


def build_dropbox_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """
    Build the authorization parameters for Dropbox OAuth.

    Args:
        oauth_config: OAuth configuration dictionary with client_id, redirect_uri, etc.
        redirect_uri: Redirect URI configured for the Dropbox application.
        scopes: List of scopes (e.g., ['files.content.read']).

    Returns:
        Dictionary of query params for the OAuth URL.
    """
    return {
        "client_id": oauth_config.get("client_id"),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "token_access_type": "offline",  # Explicitly request refresh token
    }


def build_dropbox_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """
    Build the token request data for Dropbox OAuth.

    Args:
        oauth_config: OAuth configuration dictionary.
        redirect_uri: Redirect URI used in the flow.
        scopes: Scopes list.
        auth_code: The authorization code returned from Dropbox.

    Returns:
        Dictionary of data for the token request.
    """
    return {
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }


def build_dropbox_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Build the headers for the token request to Dropbox.

    Args:
        oauth_config: OAuth configuration dictionary.

    Returns:
        Dictionary of headers for the token request.

    """
    credentials = f"{oauth_config['client_id']}:{oauth_config['client_secret']}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def build_dropbox_refresh_token_data(
    oauth_config: Dict[str, Any], refresh_token: str, credentials: Dict[str, Any]
) -> Dict[str, str]:
    """
    Build the token refresh request data for Dropbox OAuth.

    Args:
        oauth_config: OAuth configuration dictionary.
        refresh_token: The refresh token to use.
        credentials: Existing credentials.

    Returns:
        Dictionary of data for the token refresh request.
    """
    return {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": oauth_config["client_id"],
        "client_secret": oauth_config["client_secret"],
    }


def process_dropbox_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the token response from Dropbox.

    Args:
        token_response: Raw token response from Dropbox.

    Returns:
        Cleaned-up and standardized credentials dictionary.

    Raises:
        ValueError: If response is missing required access token.
    """
    if "error" in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error_description', token_response.get('error', 'Unknown error'))}"
        )

    return {
        "access_token": token_response.get("access_token"),
        "token_type": "bearer",
        "user_id": token_response.get("account_id"),
        "refresh_token": token_response.get("refresh_token"),
        "expires_in": token_response.get("expires_in"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """
    Authenticate and save credentials for Dropbox.

    Args:
        user_id: ID of the user.
        service_name: Name of the service (dropbox).
        scopes: List of scopes (e.g., ['files.content.read']).

    Returns:
        Dictionary containing final credentials (e.g., access_token).
    """
    # Get the Dropbox oauth config
    from src.auth.factory import create_auth_client

    auth_client = create_auth_client()
    oauth_config = auth_client.get_oauth_config(service_name)
    redirect_uri = oauth_config.get("redirect_uri")

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=DROPBOX_OAUTH_AUTHORIZE_URL,
        token_url=DROPBOX_OAUTH_TOKEN_URL,
        auth_params_builder=build_dropbox_auth_params,
        token_data_builder=build_dropbox_token_data,
        token_header_builder=build_dropbox_token_headers,
        process_token_response=process_dropbox_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """
    Retrieve (or refresh if needed) the access token for Dropbox.

    Args:
        user_id: ID of the user.
        service_name: Name of the service (dropbox).
        api_key: Optional API key (used by auth client abstraction).

    Returns:
        A valid access token string.
    """
    # Use refresh_token_if_needed to handle token refresh
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=DROPBOX_OAUTH_TOKEN_URL,
        token_data_builder=build_dropbox_refresh_token_data,
        process_token_response=process_dropbox_token_response,
        token_header_builder=build_dropbox_token_headers,
        api_key=api_key,
    )
