import base64
import logging
from typing import Dict, Any, List
from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed

logger = logging.getLogger(__name__)

# OAuth endpoints for Pipedrive
AUTH_URL = "https://oauth.pipedrive.com/oauth/authorize"
TOKEN_URL = "https://oauth.pipedrive.com/oauth/token"

SCOPES: list[str] = [
    "base",
    "deals:full",
    "mail:full",
    "activities:full",
    "contacts:full",
    "products:full",
    "users:read",
    "recents:read",
    "search:read",
    "admin",
    "leads:full",
    "phone-integration",
    "goals:full",
    "video-calls",
    "messengers-integration",
    "projects:full",
    "webhooks:full"
]  # Pipedrive app scopes


def build_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build authorization URL parameters for Pipedrive."""
    return {
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes) if scopes else "",
    }


def build_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], code: str
) -> Dict[str, str]:
    """Build token exchange payload for Pipedrive OAuth."""
    return {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }


def build_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """Build HTTP Basic Auth headers for token exchange."""
    client_id = oauth_config.get("client_id")
    client_secret = oauth_config.get("client_secret")
    creds = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(creds.encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def process_token_response(resp: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and return the OAuth token response."""
    if "access_token" not in resp:
        raise ValueError("No access_token in token response")
    return resp


def refresh_token_builder(
    oauth_config: Dict[str, Any], refresh_token: str, credentials: Dict[str, Any]
) -> Dict[str, Any]:
    """Build payload to refresh Pipedrive OAuth access token."""
    return {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str,
) -> Dict[str, Any]:
    """
    Run Pipedrive OAuth flow and save credentials.

    Args:
        user_id (str): The user ID to associate with the credentials
        service_name (str): The service name (e.g., 'pipedrive')
        oauth_config (Dict[str, Any]): OAuth configuration

    Returns:
        Dict[str, Any]: The OAuth token data
    """
    return run_oauth_flow(
            service_name=service_name,
            user_id=user_id,
            scopes=SCOPES,
            auth_url_base=AUTH_URL,
            token_url=TOKEN_URL,
            auth_params_builder=build_auth_params,
            token_data_builder=build_token_data,
            process_token_response=process_token_response,
            token_header_builder=build_token_headers,
        )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """
    Retrieve (or refresh if needed) the access token for Pipedrive.

    Args:
        user_id: ID of the user.
        service_name: Name of the service (pipedrive).
        api_key: Optional API key (used by auth client abstraction).

    Returns:
        A valid access token string.
    """
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=TOKEN_URL,
        token_data_builder=refresh_token_builder,
        token_header_builder=build_token_headers,
        api_key=api_key,
        return_full_credentials=True
    )
