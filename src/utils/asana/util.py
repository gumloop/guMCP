import logging
from typing import Dict, List, Any

from src.utils.oauth.util import (
    run_oauth_flow,
    refresh_token_if_needed,
)

logger = logging.getLogger(__name__)

ASANA_OAUTH_AUTHORIZE_URL = "https://app.asana.com/-/oauth_authorize"
ASANA_OAUTH_TOKEN_URL = "https://app.asana.com/-/oauth_token"


def build_asana_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """
    Build the authorization parameters for Asana OAuth.

    Args:
        oauth_config: OAuth configuration dictionary with client_id, redirect_uri, etc.
        redirect_uri: Redirect URI configured for the asana application.
        scopes: List of scopes (e.g., ['sites:read', 'sites:write']).

    Returns:
        Dictionary of query params for the OAuth URL.
    """

    return {
        "client_id": oauth_config.get("client_id"),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
    }


def build_asana_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """
    Build the token request data for Asana OAuth.

    Args:
        oauth_config: OAuth configuration dictionary.
        redirect_uri: Redirect URI used in the flow.
        scopes: Scopes list.
        auth_code: The authorization code returned from asana.

    Returns:
        Dictionary of data for the token request.
    """

    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "scope": " ".join(scopes),
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }


def build_asana_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Build the headers for the token request to Asana.

    Args:
        oauth_config: OAuth configuration dictionary.

    Returns:
        Dictionary of headers for the token request.
    """
    return {
        "Content-Type": "application/x-www-form-urlencoded",
    }


def process_asana_token_response(
    token_response: Dict[str, Any], original_scopes: List[str] = None
) -> Dict[str, Any]:
    """
    Process the token response from Asana.

    Args:
        token_response: Raw token response from Asana.

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
        "token_type": token_response.get("token_type", "Bearer"),
        "refresh_token": token_response.get("refresh_token"),
        "expires_in": token_response.get("expires_in"),
    }


def build_asana_refersh_data(
    oauth_config: Dict[str, Any], refresh_token: str, credentials_data: Dict[str, Any]
) -> Dict[str, str]:
    """Build the token refresh data for Asana Oauth"""

    scope = credentials_data.get("scope")

    return {
        "client_id": oauth_config.get("client_id"),
        "scope": scope,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_secret": oauth_config.get("client_secret"),
        "redirect_uri": oauth_config.get("redirect_uri", "http://localhost:8080"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """
    Authenticate and save credentials for asana.

    Args:
        user_id: ID of the user.
        service_name: Name of the service (asana).
        scopes: List of scopes (e.g., ['sites:read', 'sites:write']).

    Returns:
        Dictionary containing final credentials (e.g., access_token).
    """

    def process_response(response):
        return process_asana_token_response(response, scopes)

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=ASANA_OAUTH_AUTHORIZE_URL,
        token_url=ASANA_OAUTH_TOKEN_URL,
        auth_params_builder=build_asana_auth_params,
        token_data_builder=build_asana_token_data,
        process_token_response=process_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """
    Retrieve (or refresh if needed) the access token for Asana.

    Args:
        user_id: ID of the user.
        service_name: Name of the service (asana).
        api_key: Optional API key (used by auth client abstraction).

    Returns:
        A valid access token string.
    """

    access_token = await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=ASANA_OAUTH_TOKEN_URL,
        token_data_builder=build_asana_refersh_data,
        process_token_response=process_asana_token_response,
        api_key=api_key,
    )

    return access_token
