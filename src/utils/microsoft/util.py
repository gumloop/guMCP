import logging
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


def build_microsoft_refresh_data(
    oauth_config: Dict[str, Any], refresh_token: str, credentials_data: Dict[str, Any]
) -> Dict[str, str]:
    """Build the token refresh data for Microsoft OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "scope": "https://graph.microsoft.com/Mail.ReadWrite Mail.Send offline_access .default",
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_secret": oauth_config.get("client_secret"),
        "redirect_uri": oauth_config.get("redirect_uri", "http://localhost:8080"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Microsoft and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=MICROSOFT_AUTH_URL,
        token_url=MICROSOFT_TOKEN_URL,
        auth_params_builder=build_microsoft_auth_params,
        token_data_builder=build_microsoft_token_data,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Microsoft credentials, refreshing if necessary"""
    # Log information about getting the token
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=MICROSOFT_TOKEN_URL,
        token_data_builder=build_microsoft_refresh_data,
        api_key=api_key,
    )
