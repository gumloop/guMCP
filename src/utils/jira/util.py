import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed
from src.auth.factory import create_auth_client

# JIRA OAuth endpoints
JIRA_OAUTH_AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
JIRA_OAUTH_TOKEN_URL = "https://auth.atlassian.com/oauth/token"

logger = logging.getLogger(__name__)


def build_jira_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for JIRA OAuth."""
    return {
        "response_type": "code",
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "prompt": "consent",
        "state": "jira-oauth-state",
    }


def build_jira_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for JIRA OAuth."""
    return {
        "grant_type": "authorization_code",
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }


def process_jira_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process the OAuth token response returned from JIRA."""
    if "access_token" not in token_response:
        raise ValueError(f"Token exchange failed: {token_response}")

    return {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_in": token_response.get("expires_in"),
        "scope": token_response.get("scope", ""),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str], port: int = None
) -> Dict[str, Any]:
    """Authenticate with JIRA and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=JIRA_OAUTH_AUTHORIZE_URL,
        token_url=JIRA_OAUTH_TOKEN_URL,
        auth_params_builder=build_jira_auth_params,
        token_data_builder=build_jira_token_data,
        process_token_response=process_jira_token_response,
    )


async def get_credentials(
    user_id: str,
    service_name: str,
    api_key: str = None,
    return_full_credentials: bool = False,
) -> str:
    """Get JIRA credentials (access token)."""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=JIRA_OAUTH_TOKEN_URL,
        token_data_builder=lambda oauth_config, refresh_token, credentials: {
            "client_id": oauth_config.get("client_id"),
            "client_secret": oauth_config.get("client_secret"),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        process_token_response=process_jira_token_response,
        api_key=api_key,
        return_full_credentials=return_full_credentials,
    )


def format_issue_description(description: str) -> Dict[str, Any]:
    """Format a plain text description into JIRA's Atlassian Document Format (ADF)."""
    if not description:
        return None

    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": description}]}
        ],
    }


def format_comment_body(body: str) -> Dict[str, Any]:
    """Format a plain text comment into JIRA's Atlassian Document Format (ADF)."""
    return {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": body}]}
            ],
        }
    }


def format_project_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Format project creation/update payload for JIRA API."""
    payload = {
        "key": data.get("key"),
        "name": data.get("name"),
        "projectTypeKey": data.get("project_type_key", "software"),
        "leadAccountId": data.get("lead_account_id"),
    }

    if "description" in data and data["description"]:
        payload["description"] = format_issue_description(data["description"])

    return {k: v for k, v in payload.items() if v is not None}
