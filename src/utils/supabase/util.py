import logging
import time
import json
from typing import Dict, List, Any
from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


SUPABASE_AUTH_URL = "https://api.supabase.com/v1/oauth/authorize"
SUPABASE_TOKEN_URL = "https://api.supabase.com/v1/oauth/token"

logger = logging.getLogger(__name__)


def build_supabase_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Supabase OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": oauth_config.get("state", ""),
    }


def build_supabase_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Supabase OAuth."""
    return {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
    }


def process_supabase_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the token response to ensure we store necessary information.

    Supabase returns tokens in the format:
    {
        "access_token": "sbp_oauth_...",
        "refresh_token": "...",
        "expires_in": 86400,
        "token_type": "Bearer"
    }
    """
    logger.info(f"Processing Supabase token response: {token_response}")

    # If the response is a string, try to parse it as JSON
    if isinstance(token_response, str):
        try:
            token_response = json.loads(token_response)
        except json.JSONDecodeError:
            logger.error("Failed to parse token response as JSON")

    # Add expiry time if it's not already in the response
    if "expires_in" in token_response and "expires_at" not in token_response:
        token_response["expires_at"] = int(time.time()) + token_response.get(
            "expires_in", 3600
        )

    return token_response


def build_supabase_refresh_data(
    oauth_config: Dict[str, Any], refresh_token: str, credentials_data: Dict[str, Any]
) -> Dict[str, str]:
    """Build the token refresh data for Supabase OAuth."""
    return {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str
) -> Dict[str, Any]:
    """Authenticate with Supabase and save credentials"""

    # Create a wrapper for process_token_response
    def process_response(response):
        return process_supabase_token_response(response)

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=[],
        auth_url_base=SUPABASE_AUTH_URL,
        token_url=SUPABASE_TOKEN_URL,
        auth_params_builder=build_supabase_auth_params,
        token_data_builder=build_supabase_token_data,
        process_token_response=process_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Supabase credentials, refreshing if necessary"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=SUPABASE_TOKEN_URL,
        token_data_builder=build_supabase_refresh_data,
        process_token_response=process_supabase_token_response,
        api_key=api_key,
    )
