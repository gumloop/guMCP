import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


# ClickUp OAuth URLs
CLICKUP_OAUTH_AUTHORIZE_URL = "https://app.clickup.com/api"
CLICKUP_OAUTH_TOKEN_URL = "https://api.clickup.com/api/v2/oauth/token"

logger = logging.getLogger(__name__)


def build_clickup_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for ClickUp OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
        "response_type": "code",
    }


def build_clickup_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for ClickUp OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }


def process_clickup_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process ClickUp token response."""
    if not token_response.get("access_token"):
        error_msg = token_response.get("error", "Unknown error")
        error_desc = token_response.get("error_description", "")
        raise ValueError(f"Token exchange failed: {error_msg} - {error_desc}")

    # Extract and prepare credentials
    access_token = token_response.get("access_token")

    # Store necessary information
    return {
        "access_token": access_token,
        "token_type": token_response.get("token_type", "Bearer"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with ClickUp and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=CLICKUP_OAUTH_AUTHORIZE_URL,
        token_url=CLICKUP_OAUTH_TOKEN_URL,
        auth_params_builder=build_clickup_auth_params,
        token_data_builder=build_clickup_token_data,
        process_token_response=process_clickup_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get ClickUp credentials"""
    credentials = await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=CLICKUP_OAUTH_TOKEN_URL,
        token_data_builder=lambda *args: {},  # ClickUp doesn't use refresh tokens
        api_key=api_key,
    )

    # Ensure we return properly formatted access token for ClickUp API
    if isinstance(credentials, dict) and credentials.get("access_token"):
        token_type = credentials.get("token_type", "Bearer")
        return f"{token_type} {credentials['access_token']}"
    return credentials
