import base64
import logging
import secrets
from typing import Dict, List, Any

from src.utils.oauth.util import (
    run_oauth_flow,
    refresh_token_if_needed,
)


logger = logging.getLogger(__name__)

LINKEDIN_OAUTH_AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_OAUTH_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


def build_linkedin_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    # Generate a random state parameter for security
    state = secrets.token_urlsafe(16)
    return {
        "client_id": oauth_config.get("client_id"),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
    }


def build_linkedin_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    return {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
    }


def build_linkedin_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    credentials = f"{oauth_config['client_id']}:{oauth_config['client_secret']}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def build_linkedin_refresh_data(
    oauth_config: Dict[str, Any], refresh_token: str, credentials_data: Dict[str, Any]
) -> Dict[str, str]:
    """Build the token refresh data for LinkedIn OAuth."""
    return {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
    }


def process_linkedin_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    if "error" in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error_description', token_response.get('error', 'Unknown error'))}"
        )

    logger.info(f"Token response: {token_response}")
    return {
        "access_token": token_response.get("access_token"),
        "token_type": "bearer",
        "user_id": token_response.get("account_id"),
        "refresh_token": token_response.get("refresh_token"),
        "expires_in": token_response.get("expires_in"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=LINKEDIN_OAUTH_AUTHORIZE_URL,
        token_url=LINKEDIN_OAUTH_TOKEN_URL,
        auth_params_builder=build_linkedin_auth_params,
        token_data_builder=build_linkedin_token_data,
        token_header_builder=build_linkedin_token_headers,
        process_token_response=process_linkedin_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get LinkedIn credentials, refreshing if necessary"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=LINKEDIN_OAUTH_TOKEN_URL,
        token_data_builder=build_linkedin_refresh_data,
        token_header_builder=build_linkedin_token_headers,
        api_key=api_key,
    )
