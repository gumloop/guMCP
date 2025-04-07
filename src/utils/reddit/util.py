import base64
import logging
from typing import Dict, List, Any

from src.utils.oauth.util import (
    run_oauth_flow,
    refresh_token_if_needed,
)

logger = logging.getLogger(__name__)

REDDIT_OAUTH_AUTHORIZE_URL = "https://www.reddit.com/api/v1/authorize"
REDDIT_OAUTH_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"


def build_reddit_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """
    Build the authorization parameters for Reddit OAuth.

    Args:
        oauth_config: OAuth configuration dictionary with client_id, redirect_uri, etc.
        redirect_uri: Redirect URI configured for the Reddit application.
        scopes: List of scopes (e.g., ['identity', 'read', 'submit']).

    Returns:
        Dictionary of query params for the OAuth URL.
    """
    return {
        "client_id": oauth_config.get("client_id"),
        "response_type": "code",
        "state": "random_state",  # Should be randomly generated in production
        "redirect_uri": redirect_uri,
        "duration": "permanent",  # or 'temporary' for short-lived tokens
        "scope": " ".join(scopes),
    }


def build_reddit_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """
    Build the token request body for exchanging code with access token.

    Args:
        oauth_config: OAuth configuration dictionary.
        redirect_uri: Redirect URI used in the flow.
        scopes: Scopes list.
        auth_code: The authorization code returned from Reddit.

    Returns:
        POST body dictionary for token exchange.
    """
    return {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }


def build_reddit_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Build the token request headers for Reddit OAuth.

    Uses Basic Auth header with base64 encoded client_id:client_secret.

    Args:
        oauth_config: OAuth configuration dictionary.

    Returns:
        Dictionary of headers.
    """
    credentials = f'{oauth_config["client_id"]}:{oauth_config["client_secret"]}'
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    return {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "MyApp/1.0.0",  # Reddit requires a User-Agent header
    }


def process_reddit_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process Reddit's token response.

    Args:
        token_response: Raw token response JSON from Reddit.

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
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type"),
        "expires_in": token_response.get("expires_in"),
        "scope": token_response.get("scope"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """
    Authenticate with Reddit and save credentials securely.

    Args:
        user_id: ID of the user being authenticated.
        service_name: Service identifier (e.g., 'reddit').
        scopes: List of scopes (e.g., ['identity', 'read', 'submit']).

    Returns:
        Dictionary containing final credentials (e.g., access_token).
    """
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=REDDIT_OAUTH_AUTHORIZE_URL,
        token_url=REDDIT_OAUTH_TOKEN_URL,
        auth_params_builder=build_reddit_auth_params,
        token_data_builder=build_reddit_token_data,
        token_header_builder=build_reddit_token_headers,
        process_token_response=process_reddit_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """
    Retrieve (or refresh if needed) the access token for Reddit.

    Args:
        user_id: ID of the user.
        service_name: Name of the service (reddit).
        api_key: Optional API key (used by auth client abstraction).

    Returns:
        A valid access token string.
    """
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=REDDIT_OAUTH_TOKEN_URL,
        token_data_builder=lambda *args: {
            "grant_type": "refresh_token",
            "refresh_token": args[0].get("refresh_token"),
        },
        token_header_builder=build_reddit_token_headers,
        api_key=api_key,
    )
