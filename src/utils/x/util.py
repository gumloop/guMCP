import os
import json
import base64
import hashlib
import secrets
import logging
import time
from typing import Dict, Any, List, Optional

from src.utils.oauth.util import (
    run_oauth_flow,
    refresh_token_if_needed,
    generate_code_verifier,
    generate_code_challenge,
)

AUTH_URL_BASE = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"

logger = logging.getLogger(__name__)


def get_basic_auth_header(client_id: str, client_secret: str) -> str:
    """Generate Basic Authorization header for confidential client"""
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def build_token_header(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """Build headers for token exchange and refresh"""
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": get_basic_auth_header(
            oauth_config["client_id"], oauth_config["client_secret"]
        ),
    }


def process_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process token response to validate and add expires_at field"""
    if "error" in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}: {token_response.get('error_description', '')}"
        )

    if not token_response.get("access_token"):
        raise ValueError("No access token found in response")

    token_response["expires_at"] = int(time.time()) + token_response.get(
        "expires_in", 7200
    )
    return token_response


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with X and save credentials"""
    logger.info(f"Launching auth flow for user {user_id}...")

    # Generate code_verifier and code_challenge for PKCE
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    # Build state JSON with code_verifier
    state_data = {"code_verifier": code_verifier}
    state = json.dumps(state_data)

    def auth_params_builder(
        oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
    ) -> Dict[str, str]:
        """Build authorization parameters for X OAuth"""
        return {
            "response_type": "code",
            "client_id": oauth_config["client_id"],
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

    def token_data_builder(
        oauth_config: Dict[str, Any],
        redirect_uri: str,
        scopes: List[str],
        auth_code: str,
    ) -> Dict[str, str]:
        """Build token exchange data for X OAuth"""
        return {
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": oauth_config.get("code_verifier", code_verifier),
        }

    return run_oauth_flow(
        service_name,
        user_id,
        scopes,
        AUTH_URL_BASE,
        TOKEN_URL,
        auth_params_builder,
        token_data_builder,
        process_token_response,
        build_token_header,
    )


async def get_credentials(
    user_id: str, service_name: str, api_key: Optional[str] = None
) -> Any:
    """Get X API credentials for the specified user"""
    logger.info(f"Getting credentials for user {user_id}")

    # Define token data builder for refresh
    def token_data_builder(
        oauth_config: Dict[str, Any], redirect_uri: str, credentials: Dict[str, Any]
    ) -> Dict[str, str]:
        """Build token refresh data"""
        return {
            "grant_type": "refresh_token",
            "refresh_token": credentials["refresh_token"],
        }

    # Get and potentially refresh the token
    return await refresh_token_if_needed(
        user_id,
        service_name,
        TOKEN_URL,
        token_data_builder,
        process_token_response,
        build_token_header,
        api_key,
        True,  # Return full credentials
    )
