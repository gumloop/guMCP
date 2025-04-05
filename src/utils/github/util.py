import base64
import logging
from typing import Dict, List, Any
import urllib.parse

from src.utils.oauth.util import (
    run_oauth_flow,
    refresh_token_if_needed,
)

logger = logging.getLogger(__name__)

GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"


def build_github_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """
    Build the authorization parameters for GitHub OAuth.

    Args:
        oauth_config: OAuth configuration dictionary with client_id, redirect_uri, etc.
        redirect_uri: Redirect URI configured for the GitHub integration.
        scopes: List of scopes to request from GitHub.

    Returns:
        Dictionary of query params for the OAuth URL.
    """
    return {
        "client_id": oauth_config.get("client_id"),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
    }


def build_github_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """
    Build the token request body for exchanging code with access token.

    Args:
        oauth_config: OAuth configuration dictionary.
        redirect_uri: Redirect URI used in the flow.
        scopes: Scopes list (not used in token exchange).
        auth_code: The authorization code returned from GitHub.

    Returns:
        POST body dictionary for token exchange.
    """
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }


def build_github_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Build headers for GitHub token request.
    GitHub expects form-encoded data.

    Args:
        oauth_config: OAuth configuration dictionary (unused for headers).

    Returns:
        Dictionary of headers.
    """
    return {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def process_github_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process GitHub's token response.
    GitHub returns JSON data when Accept: application/json header is set.

    Args:
        token_response: JSON response from GitHub.

    Returns:
        Cleaned-up and standardized credentials dictionary.

    Raises:
        ValueError: If response is missing required access token.
    """
    if "access_token" not in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}"
        )

    return {
        "access_token": token_response.get("access_token"),
        "token_type": token_response.get("token_type", "bearer"),
        "scope": token_response.get("scope", ""),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """
    Authenticate with GitHub and save credentials securely.

    Args:
        user_id: ID of the user being authenticated.
        service_name: Service identifier (e.g., 'github').
        scopes: List of scopes to request from GitHub.

    Returns:
        Dictionary containing final credentials (e.g., access_token).
    """
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=GITHUB_OAUTH_AUTHORIZE_URL,
        token_url=GITHUB_OAUTH_TOKEN_URL,
        auth_params_builder=build_github_auth_params,
        token_data_builder=build_github_token_data,
        token_header_builder=build_github_token_headers,
        process_token_response=process_github_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """
    Retrieve (or refresh if needed) the access token for GitHub.

    Args:
        user_id: ID of the user.
        service_name: Name of the service (github).
        api_key: Optional API key (used by auth client abstraction).

    Returns:
        A valid access token string.
    """
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=GITHUB_OAUTH_TOKEN_URL,
        token_data_builder=lambda *args: {},  # GitHub doesn't support refresh tokens
        api_key=api_key,
    )
