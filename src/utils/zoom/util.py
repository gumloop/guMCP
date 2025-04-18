import base64
import logging
from typing import Dict, Any, List

from src.utils.oauth.util import (
    run_oauth_flow,
    refresh_token_if_needed,
)

logger = logging.getLogger(__name__)

ZOOM_OAUTH_AUTHORIZE_URL = "https://zoom.us/oauth/authorize"
ZOOM_OAUTH_TOKEN_URL = "https://zoom.us/oauth/token"


def build_zoom_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """
    Build the authorization parameters for Zoom OAuth.

    Args:
        oauth_config: OAuth configuration dictionary with client_id, redirect_uri, etc.
        redirect_uri: Redirect URI configured for the Zoom application.
        scopes: List of scopes (e.g., ['identity', 'read', 'submit']).

    Returns:
        Dictionary of query params for the OAuth URL.
    """
    return {
        "client_id": oauth_config.get("client_id"),
        "response_type": "code",
        "redirect_uri": redirect_uri,
    }


def build_zoom_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    return {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }


def build_zoom_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    credentials = f'{oauth_config["client_id"]}:{oauth_config["client_secret"]}'
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    return {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def process_zoom_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    if "access_token" not in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}"
        )

    return {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type"),
        "expires_in": token_response.get("expires_in"),
        "scope": token_response.get("scope"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=ZOOM_OAUTH_AUTHORIZE_URL,
        token_url=ZOOM_OAUTH_TOKEN_URL,
        auth_params_builder=build_zoom_auth_params,
        token_data_builder=build_zoom_token_data,
        token_header_builder=build_zoom_token_headers,
        process_token_response=process_zoom_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=ZOOM_OAUTH_TOKEN_URL,
        token_data_builder=lambda creds: {
            "grant_type": "refresh_token",
            "refresh_token": creds.get("refresh_token"),
        },
        token_header_builder=build_zoom_token_headers,
        api_key=api_key,
    )
