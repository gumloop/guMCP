import logging
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


# Stripe OAuth endpoints
STRIPE_OAUTH_AUTHORIZE_URL = "https://connect.stripe.com/oauth/authorize"
STRIPE_OAUTH_TOKEN_URL = "https://connect.stripe.com/oauth/token"

logger = logging.getLogger(__name__)


def build_stripe_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Stripe OAuth."""
    return {
        "response_type": "code",
        "client_id": oauth_config.get("client_id"),
        "scope": " ".join(scopes),  # Stripe uses space-separated scopes
        "redirect_uri": redirect_uri,
    }


def build_stripe_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Stripe OAuth."""
    return {
        "grant_type": "authorization_code",
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }


def process_stripe_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process the OAuth token response returned from Stripe."""
    if "access_token" not in token_response:
        raise ValueError(f"Token exchange failed: {token_response}")

    return {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get(
            "refresh_token"
        ),  # May be None in test mode
        "stripe_user_id": token_response.get("stripe_user_id"),
        "stripe_publishable_key": token_response.get("stripe_publishable_key"),
        "scope": token_response.get("scope"),
        "token_type": token_response.get("token_type"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Stripe and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=STRIPE_OAUTH_AUTHORIZE_URL,
        token_url=STRIPE_OAUTH_TOKEN_URL,
        auth_params_builder=build_stripe_auth_params,
        token_data_builder=build_stripe_token_data,
        process_token_response=process_stripe_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Stripe credentials (access token)."""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=STRIPE_OAUTH_TOKEN_URL,
        token_data_builder=lambda oauth_config, refresh_token, credentials: {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_secret": oauth_config.get("client_secret"),
        },
        process_token_response=process_stripe_token_response,
        api_key=api_key,
    )
