import logging
import time
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


TYPEFORM_OAUTH_AUTHORIZE_URL = "https://admin.typeform.com/oauth/authorize"
TYPEFORM_OAUTH_TOKEN_URL = "https://api.typeform.com/oauth/token"

logger = logging.getLogger(__name__)


def build_typeform_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Typeform OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "scope": " ".join(scopes),  # Typeform uses space-separated scopes
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": "typeform_auth",  # Simple state for security
    }


def build_typeform_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Typeform OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }


def process_typeform_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Typeform token response."""
    if not token_response.get("access_token"):
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}"
        )

    # Make sure expires_at is always set to avoid NoneType errors in refresh logic
    expires_in = token_response.get("expires_in")
    if expires_in is None:
        # Default to 1 hour if not provided
        expires_in = 3600

    # Calculate expiration time
    expires_at = int(time.time()) + expires_in

    # Typeform provides refresh tokens that we should store
    return {
        "access_token": token_response.get("access_token"),
        "token_type": token_response.get("token_type", "Bearer"),
        "refresh_token": token_response.get("refresh_token"),
        "scope": token_response.get("scope", ""),
        "expires_in": expires_in,
        "expires_at": expires_at,
    }


def build_typeform_refresh_data(
    oauth_config: Dict[str, Any], refresh_token: str
) -> Dict[str, str]:
    """Build the refresh token request data for Typeform OAuth."""
    if not refresh_token:
        # Typeform sometimes doesn't provide refresh tokens for some scopes
        logger.warning("No refresh token available for Typeform")

    return {
        "grant_type": "refresh_token",
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "refresh_token": refresh_token,
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Typeform and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=TYPEFORM_OAUTH_AUTHORIZE_URL,
        token_url=TYPEFORM_OAUTH_TOKEN_URL,
        auth_params_builder=build_typeform_auth_params,
        token_data_builder=build_typeform_token_data,
        process_token_response=process_typeform_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> Any:
    """Get Typeform credentials"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=TYPEFORM_OAUTH_TOKEN_URL,
        token_data_builder=build_typeform_refresh_data,
        process_token_response=process_typeform_token_response,
        api_key=api_key,
    )
