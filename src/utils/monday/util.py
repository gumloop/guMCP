import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed

# Monday.com OAuth endpoints
MONDAY_OAUTH_AUTHORIZE_URL = "https://auth.monday.com/oauth2/authorize"
MONDAY_OAUTH_TOKEN_URL = "https://auth.monday.com/oauth2/token"

logger = logging.getLogger(__name__)


def build_monday_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Monday.com OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "response_type": "code",
    }


def build_monday_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], code: str
) -> Dict[str, str]:
    """Build the token request data for Monday.com OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "redirect_uri": redirect_uri,
        "code": code,
        "grant_type": "authorization_code",
    }


def process_monday_token_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the token response from Monday.com OAuth."""
    return {
        "access_token": response_data.get("access_token"),
        "token_type": response_data.get("token_type"),
        "scope": response_data.get("scope"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Monday.com and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=MONDAY_OAUTH_AUTHORIZE_URL,
        token_url=MONDAY_OAUTH_TOKEN_URL,
        auth_params_builder=build_monday_auth_params,
        token_data_builder=build_monday_token_data,
        process_token_response=process_monday_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Monday.com credentials (access token)"""
    # Note: Monday.com tokens don't expire until user uninstalls the app
    # So we don't need to implement refresh token logic
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=MONDAY_OAUTH_TOKEN_URL,
        token_data_builder=lambda oauth_config, refresh_token, credentials: {
            "grant_type": "refresh_token",
            "client_id": oauth_config.get("client_id"),
            "client_secret": oauth_config.get("client_secret"),
            "refresh_token": refresh_token,
        },
        process_token_response=process_monday_token_response,
        api_key=api_key,
    )
