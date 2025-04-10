import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


CALENDLY_OAUTH_AUTHORIZE_URL = "https://auth.calendly.com/oauth/authorize"
CALENDLY_OAUTH_TOKEN_URL = "https://auth.calendly.com/oauth/token"
CALENDLY_API_URL = "https://api.calendly.com"

logger = logging.getLogger(__name__)


def build_calendly_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Calendly OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),  # Calendly uses space-separated scopes
    }


def build_calendly_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Calendly OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }


def build_calendly_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """Build headers for token request."""
    return {
        "Content-Type": "application/x-www-form-urlencoded",
    }


def process_calendly_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Calendly token response."""
    if not token_response.get("access_token"):
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}"
        )

    # Extract and prepare credentials
    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")

    # Store only what we need
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_response.get("token_type", "bearer"),
        "scope": token_response.get("scope", ""),
        "expires_in": token_response.get("expires_in"),
        "owner": token_response.get("owner"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Calendly and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=CALENDLY_OAUTH_AUTHORIZE_URL,
        token_url=CALENDLY_OAUTH_TOKEN_URL,
        auth_params_builder=build_calendly_auth_params,
        token_data_builder=build_calendly_token_data,
        process_token_response=process_calendly_token_response,
        token_header_builder=build_calendly_token_headers,
    )


def build_calendly_refresh_data(
    oauth_config: Dict[str, Any], redirect_uri: str, credentials: Dict[str, Any]
) -> Dict[str, str]:
    """Build the refresh token request data for Calendly OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "refresh_token": credentials.get("refresh_token"),
        "grant_type": "refresh_token",
    }


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Calendly credentials, refreshing if needed"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=CALENDLY_OAUTH_TOKEN_URL,
        token_data_builder=build_calendly_refresh_data,
        process_token_response=process_calendly_token_response,
        token_header_builder=build_calendly_token_headers,
        api_key=api_key,
    )
