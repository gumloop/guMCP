import logging
import time
import os
from typing import Dict, List, Any, Optional, Tuple

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed

# Zendesk OAuth endpoints
# These will be formatted with the Zendesk subdomain from config
ZENDESK_OAUTH_AUTHORIZE_URL = "https://{subdomain}.zendesk.com/oauth/authorizations/new"
ZENDESK_OAUTH_TOKEN_URL = "https://{subdomain}.zendesk.com/oauth/tokens"
ZENDESK_API_BASE_URL = "https://{subdomain}.zendesk.com/api/v2"

logger = logging.getLogger(__name__)


def build_zendesk_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Zendesk OAuth."""
    return {
        "response_type": "code",
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
    }


def build_zendesk_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Zendesk OAuth."""
    return {
        "grant_type": "authorization_code",
        "code": auth_code,
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
    }


def build_zendesk_token_header(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """Build headers for token exchange request."""
    return {
        "Content-Type": "application/x-www-form-urlencoded",
    }


def process_zendesk_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Zendesk token response."""
    if "error" in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error')}: {token_response.get('error_description', '')}"
        )

    if not token_response.get("access_token"):
        raise ValueError("No access token found in response")

    # Zendesk tokens don't expire, use 10 years default
    token_response["expires_at"] = int(time.time()) + token_response.get(
        "expires_in", 315360000
    )

    return token_response


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Zendesk and save credentials"""
    logger.info(f"Launching Zendesk auth flow for user {user_id}...")

    # Get the Zendesk subdomain from the oauth config
    from src.auth.factory import create_auth_client

    auth_client = create_auth_client()
    oauth_config = auth_client.get_oauth_config(service_name)
    subdomain = oauth_config.get("custom_subdomain", "testingmcp")

    # Construct the authorization and token URLs
    auth_url = ZENDESK_OAUTH_AUTHORIZE_URL.format(subdomain=subdomain)
    token_url = ZENDESK_OAUTH_TOKEN_URL.format(subdomain=subdomain)

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=auth_url,
        token_url=token_url,
        auth_params_builder=build_zendesk_auth_params,
        token_data_builder=build_zendesk_token_data,
        process_token_response=process_zendesk_token_response,
        token_header_builder=build_zendesk_token_header,
    )


async def get_credentials(
    user_id: str, service_name: str, api_key: Optional[str] = None
) -> str:
    """
    Get Zendesk access token

    Returns:
        Access token as a string
    """
    logger.info(f"Getting Zendesk credentials for user {user_id}")

    # Get auth client
    from src.auth.factory import create_auth_client

    auth_client = create_auth_client(api_key=api_key)

    # Get the credentials
    credentials = auth_client.get_user_credentials(service_name, user_id)

    # Check environment
    environment = os.environ.get("ENVIRONMENT", "local").lower()

    # For non-local environments where credentials contains all we need
    if environment != "local" and isinstance(credentials, dict):
        if "access_token" in credentials:
            logger.info(f"Using credentials from {environment} environment")
            return credentials["access_token"]

    # For local environment, refresh token if needed
    try:
        # Get the Zendesk subdomain from the oauth config
        oauth_config = auth_client.get_oauth_config(service_name)
        subdomain = oauth_config.get("custom_subdomain", "")
        token_url = ZENDESK_OAUTH_TOKEN_URL.format(subdomain=subdomain)

        # Define token data builder for refresh (Zendesk doesn't use refresh tokens)
        def token_data_builder(
            oauth_config: Dict[str, Any], redirect_uri: str, credentials: Dict[str, Any]
        ) -> Dict[str, str]:
            return {}

        # Get the token
        access_token = await refresh_token_if_needed(
            user_id=user_id,
            service_name=service_name,
            token_url=token_url,
            token_data_builder=token_data_builder,
            process_token_response=process_zendesk_token_response,
            token_header_builder=build_zendesk_token_header,
            api_key=api_key,
        )

        return access_token

    except Exception as e:
        # If we already have credentials with access_token, use it as fallback
        if isinstance(credentials, dict) and "access_token" in credentials:
            logger.warning(
                f"Error using OAuth config: {str(e)}. Falling back to credentials."
            )
            return credentials["access_token"]
        raise


async def get_service_config(
    user_id: str, service_name: str, api_key: Optional[str] = None
) -> Dict[str, str]:
    """
    Get service-specific configuration parameters
    """
    # Get auth client
    from src.auth.factory import create_auth_client

    auth_client = create_auth_client(api_key=api_key)

    environment = os.environ.get("ENVIRONMENT", "local").lower()

    # For non-local environments, try to get subdomain from credentials
    if environment != "local":
        credentials = auth_client.get_user_credentials(service_name, user_id)
        if isinstance(credentials, dict) and "custom_subdomain" in credentials:
            return {"custom_subdomain": credentials["custom_subdomain"]}

    # For local environment or as fallback, get from OAuth config
    try:
        oauth_config = auth_client.get_oauth_config(service_name)
        if "custom_subdomain" in oauth_config:
            return {"custom_subdomain": oauth_config["custom_subdomain"]}
        else:
            raise ValueError(
                "No Zendesk subdomain configured. Please add custom_subdomain in your configuration."
            )
    except Exception as e:
        logger.error(f"Error getting OAuth config: {str(e)}")
        raise ValueError(f"Could not retrieve Zendesk configuration: {str(e)}")
