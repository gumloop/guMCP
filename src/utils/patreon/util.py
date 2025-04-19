import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed

# Patreon OAuth endpoints
PATREON_OAUTH_AUTHORIZE_URL = "https://www.patreon.com/oauth2/authorize"
PATREON_OAUTH_TOKEN_URL = "https://www.patreon.com/api/oauth2/token"

logger = logging.getLogger(__name__)


def build_patreon_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Patreon OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "response_type": "code",
    }


def build_patreon_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], code: str
) -> Dict[str, str]:
    """Build the token request data for Patreon OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "redirect_uri": redirect_uri,
        "code": code,
        "grant_type": "authorization_code",
    }


def process_patreon_token_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the token response from Patreon OAuth."""
    return {
        "access_token": response_data.get("access_token"),
        "refresh_token": response_data.get("refresh_token"),
        "expires_in": response_data.get("expires_in"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Patreon and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=PATREON_OAUTH_AUTHORIZE_URL,
        token_url=PATREON_OAUTH_TOKEN_URL,
        auth_params_builder=build_patreon_auth_params,
        token_data_builder=build_patreon_token_data,
        process_token_response=process_patreon_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Patreon credentials (access token)"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=PATREON_OAUTH_TOKEN_URL,
        token_data_builder=lambda oauth_config, refresh_token, credentials: {
            "grant_type": "refresh_token",
            "client_id": oauth_config.get("client_id"),
            "client_secret": oauth_config.get("client_secret"),
            "refresh_token": refresh_token,
        },
        process_token_response=process_patreon_token_response,
        api_key=api_key,
    )
