import logging
from typing import Dict, List, Any
import time

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


INTERCOM_OAUTH_AUTHORIZE_URL = "https://app.intercom.com/oauth"
INTERCOM_OAUTH_TOKEN_URL = "https://api.intercom.io/auth/eagle/token"

logger = logging.getLogger(__name__)


def build_intercom_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Intercom OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "scope": " ".join(scopes),  # Intercom uses space-separated scopes
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": "intercom-auth",
    }


def build_intercom_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Intercom OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }


def process_intercom_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Intercom token response."""
    if not token_response.get("access_token"):
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}"
        )

    # Intercom doesn't use refresh tokens
    result = {
        "access_token": token_response.get("access_token"),
        "token_type": token_response.get("token_type", "Bearer"),
        "scope": token_response.get("scope", ""),
    }

    return result


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Intercom and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=INTERCOM_OAUTH_AUTHORIZE_URL,
        token_url=INTERCOM_OAUTH_TOKEN_URL,
        auth_params_builder=build_intercom_auth_params,
        token_data_builder=build_intercom_token_data,
        process_token_response=process_intercom_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Intercom credentials, refreshing if needed"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=INTERCOM_OAUTH_TOKEN_URL,
        token_data_builder=build_intercom_token_data,
        api_key=api_key,
    )
