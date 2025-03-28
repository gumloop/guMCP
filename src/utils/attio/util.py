import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


ATTIO_OAUTH_AUTHORIZE_URL = "https://app.attio.com/authorize"
ATTIO_OAUTH_TOKEN_URL = "https://app.attio.com/oauth/token"

logger = logging.getLogger(__name__)


def build_attio_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Attio OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "scope": " ".join(scopes),  # Attio uses space-delimited scopes
        "redirect_uri": redirect_uri,
        "response_type": "code",
    }


def build_attio_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Attio OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }


def build_attio_refresh_data(
    oauth_config: Dict[str, Any], refresh_token: str
) -> Dict[str, str]:
    """Build the refresh token request data for Attio OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }


def process_attio_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Attio token response."""
    if "error" in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}: {token_response.get('error_description', '')}"
        )

    if not token_response.get("access_token"):
        raise ValueError("No access token found in response")

    # Extract and prepare credentials
    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")
    expires_in = token_response.get("expires_in", 3600)  # Default to 1 hour

    # Store tokens and expiration
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_in": expires_in,
        "scope": token_response.get("scope", ""),
        "workspace_id": token_response.get("workspace_id"),
        "workspace_name": token_response.get("workspace_name"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Attio and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=ATTIO_OAUTH_AUTHORIZE_URL,
        token_url=ATTIO_OAUTH_TOKEN_URL,
        auth_params_builder=build_attio_auth_params,
        token_data_builder=build_attio_token_data,
        process_token_response=process_attio_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> Any:
    """Get Attio credentials, refreshing if needed"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=ATTIO_OAUTH_TOKEN_URL,
        token_data_builder=build_attio_refresh_data,
        process_token_response=process_attio_token_response,
        api_key=api_key,
    )
