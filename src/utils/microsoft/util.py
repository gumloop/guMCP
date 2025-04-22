import logging
import time
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

logger = logging.getLogger(__name__)


def build_microsoft_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Microsoft OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "response_mode": "query",
    }


def build_microsoft_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Microsoft OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "scope": " ".join(scopes),
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "client_secret": oauth_config.get("client_secret"),
    }


def process_microsoft_token_response(
    token_response: Dict[str, Any], original_scopes: List[str] = None
) -> Dict[str, Any]:
    """Process the token response to ensure we store necessary information."""
    # Add expiry time
    token_response["expires_at"] = int(time.time()) + token_response.get(
        "expires_in", 3600
    )

    # Ensure scope is included in the credentials
    if "scope" not in token_response:
        # Check if scope is in response params
        if "scope" in token_response.get("params", {}):
            token_response["scope"] = token_response["params"]["scope"]
        # If original_scopes were provided, use them
        elif original_scopes:
            token_response["scope"] = " ".join(original_scopes)

    return token_response


def build_microsoft_refresh_data(
    oauth_config: Dict[str, Any], refresh_token: str, credentials_data: Dict[str, Any]
) -> Dict[str, str]:
    """Build the token refresh data for Microsoft OAuth."""
    # Use the original scope if available in credentials_data, otherwise use a default scope
    # This ensures we refresh with the same scopes that were originally requested
    scope = credentials_data.get("scope", "offline_access")

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
    """Authenticate with Microsoft and save credentials"""

    # Create a wrapper for process_token_response to include the original scopes
    def process_response(response):
        return process_microsoft_token_response(response, scopes)

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=MICROSOFT_AUTH_URL,
        token_url=MICROSOFT_TOKEN_URL,
        auth_params_builder=build_microsoft_auth_params,
        token_data_builder=build_microsoft_token_data,
        process_token_response=process_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Microsoft credentials, refreshing if necessary"""
    # Log information about getting the token
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=MICROSOFT_TOKEN_URL,
        token_data_builder=build_microsoft_refresh_data,
        process_token_response=process_microsoft_token_response,
        api_key=api_key,
    )
