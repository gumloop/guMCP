import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


LINEAR_OAUTH_AUTHORIZE_URL = "https://linear.app/oauth/authorize"
LINEAR_OAUTH_TOKEN_URL = "https://api.linear.app/oauth/token"
LINEAR_OAUTH_REVOKE_URL = "https://api.linear.app/oauth/revoke"

logger = logging.getLogger(__name__)


def build_linear_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Linear OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "scope": ",".join(scopes),  # Linear uses comma-separated scopes
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "actor": "user",  # Default to user actor mode
    }


def build_linear_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Linear OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }


def process_linear_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Linear token response."""
    if not token_response.get("access_token"):
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}"
        )

    # Extract and prepare credentials
    access_token = token_response.get("access_token")

    # Store only what we need
    return {
        "access_token": access_token,
        "token_type": token_response.get("token_type", "Bearer"),
        "scope": token_response.get("scope", ""),
        "expires_in": token_response.get("expires_in"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Linear and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=LINEAR_OAUTH_AUTHORIZE_URL,
        token_url=LINEAR_OAUTH_TOKEN_URL,
        auth_params_builder=build_linear_auth_params,
        token_data_builder=build_linear_token_data,
        process_token_response=process_linear_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Linear credentials"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=LINEAR_OAUTH_TOKEN_URL,
        token_data_builder=lambda *args: {},  # Linear doesn't use refresh tokens
        api_key=api_key,
    )
