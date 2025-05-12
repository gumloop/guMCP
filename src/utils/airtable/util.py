import base64
import logging

from typing import Dict, List, Any

from src.utils.oauth.util import (
    run_oauth_flow,
    refresh_token_if_needed,
    generate_code_verifier,
    generate_code_challenge,
)


AIRTABLE_OAUTH_AUTHORIZE_URL = "https://airtable.com/oauth2/v1/authorize"
AIRTABLE_OAUTH_TOKEN_URL = "https://airtable.com/oauth2/v1/token"

logger = logging.getLogger(__name__)


def build_airtable_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Airtable OAuth."""
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    # Store code_verifier in oauth_config for later use
    oauth_config["code_verifier"] = code_verifier
    return {
        "client_id": oauth_config.get("client_id"),
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": f'{{"code_verifier":"{code_verifier}"}}',
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }


def build_airtable_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Airtable OAuth."""
    return {
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code_verifier": oauth_config.get("code_verifier"),
    }


def process_airtable_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Airtable token response."""
    if "access_token" not in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}"
        )

    # Store token details
    return {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_in": token_response.get("expires_in"),
        "scope": token_response.get("scope", ""),
    }


def build_airtable_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """Build the token request headers for Airtable OAuth."""
    # Concatenate client_id and client_secret with a colon
    credentials = f'{oauth_config.get("client_id")}:{oauth_config.get("client_secret")}'

    # Encode the credentials in base64 format
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}",
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Airtable and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=AIRTABLE_OAUTH_AUTHORIZE_URL,
        token_url=AIRTABLE_OAUTH_TOKEN_URL,
        auth_params_builder=build_airtable_auth_params,
        token_data_builder=build_airtable_token_data,
        token_header_builder=build_airtable_token_headers,
        process_token_response=process_airtable_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Airtable credentials, refreshing if needed"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=AIRTABLE_OAUTH_TOKEN_URL,
        token_data_builder=lambda oauth_config, refresh_token, scopes: {
            "client_id": oauth_config["client_id"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(scopes),
        },
        token_header_builder=build_airtable_token_headers,
        api_key=api_key,
    )
