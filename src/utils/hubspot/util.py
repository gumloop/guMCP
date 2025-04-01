import logging
import time
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


HUBSPOT_OAUTH_AUTHORIZE_URL = "https://app.hubspot.com/oauth/authorize"
HUBSPOT_OAUTH_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"

logger = logging.getLogger(__name__)


def build_hubspot_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for HubSpot OAuth."""
    # Format scopes for HubSpot - they need to be space-separated and properly encoded
    formatted_scopes = " ".join(scopes)

    return {
        "client_id": oauth_config.get("client_id"),
        "scope": formatted_scopes,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "optional_scope": "",  # Add empty optional scope parameter
    }


def build_hubspot_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for HubSpot OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }


def build_hubspot_refresh_data(
    oauth_config: Dict[str, Any], refresh_token: str
) -> Dict[str, str]:
    """Build the refresh token request data for HubSpot OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }


def process_hubspot_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process HubSpot token response."""
    if "error" in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}: {token_response.get('error_description', '')}"
        )

    if not token_response.get("access_token"):
        raise ValueError("No access token found in response")

    # Extract and prepare credentials
    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")
    expires_in = token_response.get("expires_in", 3600)  # Default to 1 hour
    # Use the expires_at value from the token response if available
    if "expires_at" in token_response:
        token_response["expires_at"] = token_response["expires_at"]
    else:
        token_response["expires_at"] = int(time.time()) + expires_in

    # Store tokens and expiration
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_in": expires_in,
        "expires_at": token_response.get("expires_at"),
        "scope": token_response.get("scope", ""),
        "hub_id": token_response.get("hub_id"),
        "hub_domain": token_response.get("hub_domain"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with HubSpot and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=HUBSPOT_OAUTH_AUTHORIZE_URL,
        token_url=HUBSPOT_OAUTH_TOKEN_URL,
        auth_params_builder=build_hubspot_auth_params,
        token_data_builder=build_hubspot_token_data,
        process_token_response=process_hubspot_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> Any:
    """Get HubSpot credentials, refreshing if needed"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=HUBSPOT_OAUTH_TOKEN_URL,
        token_data_builder=build_hubspot_refresh_data,
        process_token_response=process_hubspot_token_response,
        api_key=api_key,
    )
