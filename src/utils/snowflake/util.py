import base64
import logging
from typing import Dict, List, Any

from src.utils.oauth.util import (
    run_oauth_flow,
    refresh_token_if_needed,
)

logger = logging.getLogger(__name__)

# Snowflake OAuth endpoints
SNOWFLAKE_OAUTH_AUTHORIZE_URL = (
    "https://{account}.snowflakecomputing.com/oauth/authorize"
)
SNOWFLAKE_OAUTH_TOKEN_URL = (
    "https://{account}.snowflakecomputing.com/oauth/token-request"
)


def build_snowflake_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """
    Build the authorization parameters for Snowflake OAuth.

    Args:
        oauth_config: OAuth configuration dictionary with client_id, redirect_uri, etc.
        redirect_uri: Redirect URI configured for the Snowflake application.
        scopes: List of scopes (e.g., ['session:role:any']).

    Returns:
        Dictionary of query params for the OAuth URL.
    """
    return {
        "client_id": oauth_config.get("client_id"),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
    }


def build_snowflake_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """
    Build the token request data for Snowflake OAuth.

    Args:
        oauth_config: OAuth configuration dictionary.
        redirect_uri: Redirect URI used in the flow.
        scopes: Scopes list.
        auth_code: The authorization code returned from Snowflake.

    Returns:
        POST body dictionary for token exchange.
    """
    return {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
    }


def build_snowflake_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Build the token request headers for Snowflake OAuth.

    Uses Basic Auth header with base64 encoded client_id:client_secret.

    Args:
        oauth_config: OAuth configuration dictionary.

    Returns:
        Dictionary of headers.
    """
    credentials = f'{oauth_config["client_id"]}:{oauth_config["client_secret"]}'
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    return {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def process_snowflake_token_response(
    token_response: Dict[str, Any], account: str
) -> Dict[str, Any]:
    """
    Process Snowflake token response.

    Args:
        token_response: Raw token response JSON from Snowflake.
        account: Snowflake account identifier.

    Returns:
        Cleaned-up and standardized credentials dictionary.

    Raises:
        ValueError: If response is missing required access token.
    """
    if "error" in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error_description', token_response.get('error', 'Unknown error'))}"
        )

    return {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_in": token_response.get("expires_in"),
        "scope": token_response.get("scope", ""),
        "username": token_response.get("username"),
        "account": account,
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """
    Authenticate with Snowflake and save credentials securely.

    Args:
        user_id: ID of the user being authenticated.
        service_name: Service identifier (e.g., 'snowflake').
        scopes: List of scopes (e.g., ['session:role:any']).

    Returns:
        Dictionary containing final credentials (e.g., access_token).
    """
    # Get the Snowflake account from the oauth config
    from src.auth.factory import create_auth_client

    auth_client = create_auth_client()
    oauth_config = auth_client.get_oauth_config(service_name)
    account = oauth_config.get("account")
    # Construct the authorization and token URLs
    auth_url = SNOWFLAKE_OAUTH_AUTHORIZE_URL.format(account=account)
    token_url = SNOWFLAKE_OAUTH_TOKEN_URL.format(account=account)

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=auth_url,
        token_url=token_url,
        auth_params_builder=build_snowflake_auth_params,
        token_data_builder=build_snowflake_token_data,
        token_header_builder=build_snowflake_token_headers,
        process_token_response=lambda response: process_snowflake_token_response(
            response, account
        ),
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """
    Retrieve (or refresh if needed) the access token for Snowflake.

    Args:
        user_id: ID of the user.
        service_name: Name of the service (snowflake).
        api_key: Optional API key (used by auth client abstraction).

    Returns:
        A valid access token string.
    """
    # Get the Snowflake account from the oauth config
    from src.auth.factory import create_auth_client

    auth_client = create_auth_client()
    oauth_config = auth_client.get_oauth_config(service_name)
    account = oauth_config.get("account")
    token_url = SNOWFLAKE_OAUTH_TOKEN_URL.format(account=account)

    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=token_url,
        token_data_builder=lambda credentials, oauth_config: {
            "grant_type": "refresh_token",
            "refresh_token": credentials.get("refresh_token"),
            "client_id": oauth_config.get("client_id"),
            "client_secret": oauth_config.get("client_secret"),
        },
        token_header_builder=build_snowflake_token_headers,
        api_key=api_key,
    )
