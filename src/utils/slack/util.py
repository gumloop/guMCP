import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


SLACK_OAUTH_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_OAUTH_TOKEN_URL = "https://slack.com/api/oauth.v2.access"

logger = logging.getLogger(__name__)


def build_slack_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Slack OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "scope": ",".join(scopes),
        "redirect_uri": redirect_uri,
    }


def build_slack_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Slack OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }


def process_slack_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Slack token response."""
    if not token_response.get("ok"):
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}"
        )

    # Extract and prepare credentials
    access_token = token_response.get("access_token")

    # Store only what we need
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "scope": token_response.get("scope", ""),
        "team_id": token_response.get("team", {}).get("id"),
        "team_name": token_response.get("team", {}).get("name"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Slack and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=SLACK_OAUTH_AUTHORIZE_URL,
        token_url=SLACK_OAUTH_TOKEN_URL,
        auth_params_builder=build_slack_auth_params,
        token_data_builder=build_slack_token_data,
        process_token_response=process_slack_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Slack credentials"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=SLACK_OAUTH_TOKEN_URL,
        token_data_builder=lambda *args: {},  # Slack doesn't use refresh tokens
        api_key=api_key,
    )
