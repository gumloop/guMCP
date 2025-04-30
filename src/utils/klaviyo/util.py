import base64
import hashlib
import logging
import os
from typing import Dict, List, Any
from src.utils.oauth.util import (
    run_oauth_flow,
    refresh_token_if_needed,
)

logger = logging.getLogger(__name__)

# Klaviyo OAuth endpoints
KLAVIYO_OAUTH_AUTHORIZE_URL = "https://www.klaviyo.com/oauth/authorize"
KLAVIYO_OAUTH_TOKEN_URL = "https://a.klaviyo.com/oauth/token"


def generate_code_challenge() -> tuple:
    """
    Generate a PKCE code verifier and challenge for Klaviyo OAuth.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    verifier_bytes = os.urandom(32)
    code_verifier = (
        base64.urlsafe_b64encode(verifier_bytes).rstrip(b"=").decode("utf-8")
    )
    challenge_bytes = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = (
        base64.urlsafe_b64encode(challenge_bytes).rstrip(b"=").decode("utf-8")
    )
    return code_verifier, code_challenge


def build_klaviyo_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """
    Build the authorization parameters for Klaviyo OAuth.

    Args:
        oauth_config: OAuth configuration dictionary with client_id, redirect_uri, etc.
        redirect_uri: Redirect URI configured for the Klaviyo application.
        scopes: List of scopes (e.g., ['list:read', 'list:write']).

    Returns:
        Dictionary of query params for the OAuth URL.
    """
    code_verifier, code_challenge = generate_code_challenge()

    # Store the code_verifier in the oauth_config for later use
    oauth_config["code_verifier"] = code_verifier

    return {
        "client_id": oauth_config.get("client_id"),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
    }


def build_klaviyo_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """
    Build the token request data for Klaviyo OAuth.

    Args:
        oauth_config: OAuth configuration dictionary.
        redirect_uri: Redirect URI used in the flow.
        scopes: Scopes list.
        auth_code: The authorization code returned from Klaviyo.

    Returns:
        POST body dictionary for token exchange.
    """
    return {
        "grant_type": "authorization_code",
        "code": auth_code,
        "code_verifier": oauth_config.get("code_verifier"),
        "redirect_uri": redirect_uri,
    }


def build_klaviyo_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Build the token request headers for Klaviyo OAuth.

    Uses Basic Auth header with base64 encoded client_id:secret_key.

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
    }


def process_klaviyo_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process Klaviyo token response.

    Args:
        token_response: Raw token response JSON from Klaviyo.

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
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_in": token_response.get("expires_in"),
        "scope": token_response.get("scope", ""),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """
    Authenticate with Klaviyo and save credentials securely.

    Args:
        user_id: ID of the user being authenticated.
        service_name: Service identifier (e.g., 'klaviyo').
        scopes: List of scopes (e.g., ['list:read', 'list:write']).

    Returns:
        Dictionary containing final credentials (e.g., access_token).
    """
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=KLAVIYO_OAUTH_AUTHORIZE_URL,
        token_url=KLAVIYO_OAUTH_TOKEN_URL,
        auth_params_builder=build_klaviyo_auth_params,
        token_data_builder=build_klaviyo_token_data,
        token_header_builder=build_klaviyo_token_headers,
        process_token_response=process_klaviyo_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """
    Retrieve (or refresh if needed) the access token for Klaviyo.

    Args:
        user_id: ID of the user.
        service_name: Name of the service (klaviyo).
        api_key: Optional API key (used by auth client abstraction).

    Returns:
        A valid access token string.
    """
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=KLAVIYO_OAUTH_TOKEN_URL,
        token_data_builder=lambda credentials, oauth_config: {
            "grant_type": "refresh_token",
            "refresh_token": credentials.get("refresh_token"),
        },
        token_header_builder=build_klaviyo_token_headers,
        api_key=api_key,
    )
