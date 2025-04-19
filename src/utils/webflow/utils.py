import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


WEBFLOW_OAUTH_AUTHORIZE_URL = "https://webflow.com/oauth/authorize"
WEBFLOW_OAUTH_TOKEN_URL = "https://api.webflow.com/oauth/access_token"

logger = logging.getLogger(__name__)


def build_webflow_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Webflow OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "scope": " ".join(scopes),  # Webflow uses space-separated scopes
        "redirect_uri": redirect_uri,
        "response_type": "code",
    }


def build_webflow_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Webflow OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }


def process_webflow_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Webflow token response."""
    if not token_response.get("access_token"):
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}"
        )

    # Store only what we need
    return {**token_response}


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Webflow and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=WEBFLOW_OAUTH_AUTHORIZE_URL,
        token_url=WEBFLOW_OAUTH_TOKEN_URL,
        auth_params_builder=build_webflow_auth_params,
        token_data_builder=build_webflow_token_data,
        process_token_response=process_webflow_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Webflow credentials"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=WEBFLOW_OAUTH_TOKEN_URL,
        token_data_builder=build_webflow_token_data,
        api_key=api_key,
    )
