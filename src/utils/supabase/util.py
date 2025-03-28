import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed

SUPABASE_OAUTH_AUTHORIZE_URL = "https://api.supabase.com/v1/oauth/authorize"
SUPABASE_OAUTH_TOKEN_URL = "https://api.supabase.com/v1/oauth/token"

logger = logging.getLogger(__name__)


def build_supabase_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Supabase OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "scope": " ".join(scopes),  # Supabase uses space-separated scopes
        "redirect_uri": redirect_uri,
        "response_type": "code",
    }


def build_supabase_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Supabase OAuth."""
    return {
        "grant_type": "authorization_code",
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }


def process_supabase_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Supabase token response."""
    if "access_token" not in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'No access token in response')}"
        )

    # Extract and prepare credentials
    return {
        "access_token": token_response["access_token"],
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_in": token_response.get("expires_in"),
        "scope": token_response.get("scope", ""),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str] = None
) -> Dict[str, Any]:
    """Authenticate with Supabase and save credentials"""
    if scopes is None:
        scopes = ["all"]  # Default scope for Supabase Management API

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=SUPABASE_OAUTH_AUTHORIZE_URL,
        token_url=SUPABASE_OAUTH_TOKEN_URL,
        auth_params_builder=build_supabase_auth_params,
        token_data_builder=build_supabase_token_data,
        process_token_response=process_supabase_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Supabase credentials, refreshing if necessary"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=SUPABASE_OAUTH_TOKEN_URL,
        token_data_builder=build_supabase_token_data,
        api_key=api_key,
    )
