import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


QUICKBOOKS_OAUTH_AUTHORIZE_URL = "https://appcenter.intuit.com/connect/oauth2"
QUICKBOOKS_OAUTH_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
QUICKBOOKS_OAUTH_REVOKE_URL = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"

logger = logging.getLogger(__name__)


def build_quickbooks_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for QuickBooks OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "scope": " ".join(scopes),  # QuickBooks uses space-separated scopes
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": "random_state",  # In production, use a secure random string
    }


def build_quickbooks_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for QuickBooks OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }


def build_quickbooks_refresh_token_data(
    oauth_config: Dict[str, Any],
    refresh_token: str,
    credentials_data: Dict[str, Any] = None,
) -> Dict[str, str]:
    """Build the refresh token request data for QuickBooks OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }


def process_quickbooks_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process QuickBooks token response."""
    if not token_response.get("access_token"):
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}"
        )

    # Store credentials
    return {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_in": token_response.get("expires_in"),
        "x_refresh_token_expires_in": token_response.get("x_refresh_token_expires_in"),
        "realmId": token_response.get("realmId"),  # Store QuickBooks company ID
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with QuickBooks and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=QUICKBOOKS_OAUTH_AUTHORIZE_URL,
        token_url=QUICKBOOKS_OAUTH_TOKEN_URL,
        auth_params_builder=build_quickbooks_auth_params,
        token_data_builder=build_quickbooks_token_data,
        process_token_response=process_quickbooks_token_response,
    )


async def get_credentials(
    user_id: str, service_name: str, api_key: str = None
) -> Dict[str, Any]:
    """Get QuickBooks credentials with refresh token handling"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=QUICKBOOKS_OAUTH_TOKEN_URL,
        token_data_builder=build_quickbooks_refresh_token_data,
        api_key=api_key,
        return_full_credentials=True,  # Return the complete credentials dict, not just the token
    )
