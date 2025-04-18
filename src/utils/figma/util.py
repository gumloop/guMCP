import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed

# Figma OAuth endpoints
FIGMA_OAUTH_AUTHORIZE_URL = "https://www.figma.com/oauth"
FIGMA_OAUTH_TOKEN_URL = "https://api.figma.com/v1/oauth/token"

logger = logging.getLogger(__name__)


def build_figma_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Figma OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),  # Figma uses space-separated scopes
        "state": "figma_auth",  # Simple state for security
        "response_type": "code",
    }


def build_figma_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], code: str
) -> Dict[str, str]:
    """Build the token request data for Figma OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "redirect_uri": redirect_uri,
        "code": code,
        "grant_type": "authorization_code",
    }


def build_figma_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """Build the token request headers for Figma OAuth."""
    import base64

    credentials = f"{oauth_config.get('client_id')}:{oauth_config.get('client_secret')}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def process_figma_token_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the token response from Figma OAuth."""
    return {
        "access_token": response_data.get("access_token"),
        "refresh_token": response_data.get("refresh_token"),
        "expires_in": response_data.get("expires_in"),
        "user_id": response_data.get("user_id"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Figma and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=FIGMA_OAUTH_AUTHORIZE_URL,
        token_url=FIGMA_OAUTH_TOKEN_URL,
        auth_params_builder=build_figma_auth_params,
        token_data_builder=build_figma_token_data,
        token_header_builder=build_figma_token_headers,
        process_token_response=process_figma_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Figma credentials (access token)"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=FIGMA_OAUTH_TOKEN_URL,
        token_data_builder=lambda oauth_config, refresh_token, credentials: {
            "grant_type": "refresh_token",
            "client_id": oauth_config.get("client_id"),
            "client_secret": oauth_config.get("client_secret"),
            "refresh_token": refresh_token,
        },
        token_header_builder=build_figma_token_headers,
        process_token_response=process_figma_token_response,
        api_key=api_key,
    )
