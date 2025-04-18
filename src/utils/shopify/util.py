import logging
import time
import os
from typing import Dict, List, Any, Optional, Tuple

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed

# Shopify OAuth endpoints
SHOPIFY_OAUTH_AUTHORIZE_URL = (
    "https://{custom_subdomain}.myshopify.com/admin/oauth/authorize"
)
SHOPIFY_OAUTH_TOKEN_URL = (
    "https://{custom_subdomain}.myshopify.com/admin/oauth/access_token"
)
SHOPIFY_API_BASE_URL = (
    "https://{custom_subdomain}.myshopify.com/admin/api/{api_version}"
)

logger = logging.getLogger(__name__)


def build_shopify_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Shopify OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
        "scope": ",".join(scopes),
        "state": oauth_config.get("state", ""),
    }


def build_shopify_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Shopify OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }


def build_shopify_token_header(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """Build headers for token exchange request."""
    return {
        "Content-Type": "application/x-www-form-urlencoded",
    }


def process_shopify_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Shopify token response."""
    if "error" in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error')}: {token_response.get('error_description', '')}"
        )

    if not token_response.get("access_token"):
        raise ValueError("No access token found in response")

    # Shopify access tokens don't expire by default
    # Set a very long expiry (10 years) for token management
    token_response["expires_at"] = int(time.time()) + 315360000

    # Store the custom_subdomain if provided in response
    if "custom_subdomain" in token_response and "shop_url" not in token_response:
        token_response["shop_url"] = f"https://{token_response['custom_subdomain']}"

    return token_response


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Shopify and save credentials"""
    logger.info(f"Launching Shopify auth flow for user {user_id}...")

    # Get the Shopify config
    from src.auth.factory import create_auth_client

    auth_client = create_auth_client()
    oauth_config = auth_client.get_oauth_config(service_name)

    # Get custom_subdomain from oauth config
    custom_subdomain = oauth_config.get("custom_subdomain")
    if not custom_subdomain:
        raise ValueError(
            "No custom_subdomain configured in oauth.json. Please add 'custom_subdomain' parameter with your Shopify store name (without .myshopify.com)"
        )

    # Generate a random state parameter if not provided
    if "state" not in oauth_config:
        oauth_config["state"] = os.urandom(16).hex()

    # Construct the authorization and token URLs
    auth_url = SHOPIFY_OAUTH_AUTHORIZE_URL.format(custom_subdomain=custom_subdomain)
    token_url = SHOPIFY_OAUTH_TOKEN_URL.format(custom_subdomain=custom_subdomain)

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=auth_url,
        token_url=token_url,
        auth_params_builder=build_shopify_auth_params,
        token_data_builder=build_shopify_token_data,
        process_token_response=process_shopify_token_response,
        token_header_builder=build_shopify_token_header,
    )


async def get_credentials(
    user_id: str, service_name: str, api_key: Optional[str] = None
) -> str:
    """
    Get Shopify access token

    Returns:
        Access token as a string
    """
    logger.info(f"Getting Shopify credentials for user {user_id}")

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

    # For local environment, Shopify tokens don't expire, but let's keep the pattern
    try:
        # Get the custom_subdomain from the config or credentials
        oauth_config = auth_client.get_oauth_config(service_name)
        custom_subdomain = oauth_config.get("custom_subdomain") or (
            credentials.get("custom_subdomain") if credentials else None
        )

        if not custom_subdomain:
            raise ValueError("No custom_subdomain found in config or credentials")

        token_url = SHOPIFY_OAUTH_TOKEN_URL.format(custom_subdomain=custom_subdomain)

        # Define token data builder for refresh (Shopify doesn't use refresh tokens)
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
            process_token_response=process_shopify_token_response,
            token_header_builder=build_shopify_token_header,
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

    # Get credentials to extract custom_subdomain information
    credentials = auth_client.get_user_credentials(service_name, user_id)

    # Try to get custom_subdomain from credentials
    if isinstance(credentials, dict) and "custom_subdomain" in credentials:
        return {
            "custom_subdomain": credentials["custom_subdomain"],
            "api_version": credentials.get("api_version", "2024-07"),
        }

    # If not in credentials, try OAuth config
    try:
        oauth_config = auth_client.get_oauth_config(service_name)
        if "custom_subdomain" in oauth_config:
            return {
                "custom_subdomain": oauth_config["custom_subdomain"],
                "api_version": oauth_config.get("api_version", "2024-07"),
            }
        else:
            raise ValueError(
                "No Shopify custom_subdomain configured. Please add custom_subdomain parameter in your configuration."
            )
    except Exception as e:
        logger.error(f"Error getting OAuth config: {str(e)}")
        raise ValueError(f"Could not retrieve Shopify configuration: {str(e)}")
