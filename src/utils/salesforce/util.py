import logging
import time
import os
from typing import Dict, List, Any, Optional

from src.utils.oauth.util import (
    run_oauth_flow,
    refresh_token_if_needed,
    generate_code_verifier,
    generate_code_challenge,
)

# Salesforce OAuth endpoints
# These will be formatted with the Salesforce subdomain from config
SALESFORCE_OAUTH_AUTHORIZE_URL = "https://{subdomain}.my.salesforce.com/services/oauth2/authorize"
SALESFORCE_OAUTH_TOKEN_URL = "https://{subdomain}.my.salesforce.com/services/oauth2/token"
SALESFORCE_API_BASE_URL = "https://{subdomain}.my.salesforce.com/services/data/v52.0"

logger = logging.getLogger(__name__)


def build_salesforce_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Salesforce OAuth."""
    # Generate PKCE code verifier and challenge
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    # Store code_verifier in oauth_config for later use
    oauth_config["code_verifier"] = code_verifier

    return {
        "client_id": oauth_config.get("client_id"),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }


def build_salesforce_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Salesforce OAuth."""
    return {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code_verifier": oauth_config.get("code_verifier"),
    }


def build_salesforce_token_header(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """Build headers for token exchange request."""
    return {
        "Content-Type": "application/x-www-form-urlencoded",
    }


def process_salesforce_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Salesforce token response."""
    if "error" in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error_description', token_response.get('error', 'Unknown error'))}"
        )

    if not token_response.get("access_token"):
        raise ValueError("No access token found in response")

    return {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_in": token_response.get("expires_in"),
        "scope": token_response.get("scope", ""),
        "username": token_response.get("username"),
        "instance_url": token_response.get("instance_url"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Salesforce and save credentials"""
    logger.info(f"Launching Salesforce auth flow for user {user_id}...")

    # Get the Salesforce subdomain from the oauth config
    from src.auth.factory import create_auth_client

    auth_client = create_auth_client()
    oauth_config = auth_client.get_oauth_config(service_name)
    subdomain = oauth_config.get("custom_subdomain", "login")

    # Construct the authorization and token URLs
    auth_url = SALESFORCE_OAUTH_AUTHORIZE_URL.format(subdomain=subdomain)
    token_url = SALESFORCE_OAUTH_TOKEN_URL.format(subdomain=subdomain)

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=auth_url,
        token_url=token_url,
        auth_params_builder=build_salesforce_auth_params,
        token_data_builder=build_salesforce_token_data,
        process_token_response=process_salesforce_token_response,
        token_header_builder=build_salesforce_token_header,
    )


async def get_credentials(
    user_id: str, service_name: str, api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get Salesforce access token and instance URL

    Returns:
        Dictionary with access_token and instance_url
    """
    logger.info(f"Getting Salesforce credentials for user {user_id}")

    # Get auth client
    from src.auth.factory import create_auth_client

    auth_client = create_auth_client(api_key=api_key)

    # Get the credentials
    credentials = auth_client.get_user_credentials(service_name, user_id)

    # Check environment
    environment = os.environ.get("ENVIRONMENT", "local").lower()

    # For non-local environments where credentials contains all we need
    if environment != "local" and isinstance(credentials, dict):
        if "access_token" in credentials and "instance_url" in credentials:
            logger.info(f"Using credentials from {environment} environment")
            return {
                "access_token": credentials["access_token"],
                "instance_url": credentials["instance_url"],
            }

    # For local environment, refresh token if needed
    try:
        # Get the Salesforce subdomain from the oauth config
        oauth_config = auth_client.get_oauth_config(service_name)
        subdomain = oauth_config.get("custom_subdomain", "login")
        token_url = SALESFORCE_OAUTH_TOKEN_URL.format(subdomain=subdomain)

        # Define token data builder for refresh
        def token_data_builder(
            oauth_config: Dict[str, Any], redirect_uri: str, credentials: Dict[str, Any]
        ) -> Dict[str, str]:
            return {
                "grant_type": "refresh_token",
                "refresh_token": credentials.get("refresh_token"),
                "client_id": oauth_config.get("client_id"),
                "client_secret": oauth_config.get("client_secret"),
            }

        # Get the token
        credentials = await refresh_token_if_needed(
            user_id=user_id,
            service_name=service_name,
            token_url=token_url,
            token_data_builder=token_data_builder,
            process_token_response=process_salesforce_token_response,
            token_header_builder=build_salesforce_token_header,
            api_key=api_key,
            return_full_credentials=True,
        )

        return credentials

    except Exception as e:
        # If we already have credentials with access_token, use it as fallback
        if isinstance(credentials, dict) and "access_token" in credentials and "instance_url" in credentials:
            logger.warning(
                f"Error using OAuth config: {str(e)}. Falling back to existing credentials."
            )
            return {
                "access_token": credentials["access_token"],
                "instance_url": credentials["instance_url"],
            }
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
                "No Salesforce subdomain configured. Please add custom_subdomain in your configuration."
            )
    except Exception as e:
        logger.error(f"Error getting OAuth config: {str(e)}")
        raise ValueError(f"Could not retrieve Salesforce configuration: {str(e)}")
