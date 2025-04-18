import logging
import base64
import hashlib
import secrets
import json
from typing import Dict, List, Any

from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed

# Canva OAuth endpoints
CANVA_OAUTH_AUTHORIZE_URL = "https://www.canva.com/api/oauth/authorize"
CANVA_OAUTH_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"  # Updated token URL

# Default scopes for Canva OAuth

logger = logging.getLogger(__name__)


def generate_code_verifier() -> str:
    """Generate a code verifier for PKCE."""
    return secrets.token_urlsafe(96)[:128]  # Ensure it's not longer than 128 chars


def generate_code_challenge(code_verifier: str) -> str:
    """Generate a code challenge from the code verifier using SHA-256."""
    sha256_hash = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(sha256_hash).decode().rstrip("=")


def build_canva_auth_params(
    oauth_config: Dict[str, Any],
    redirect_uri: str,
    scopes: List[str],
    code_challenge: str = None,
) -> Dict[str, str]:
    """Build the authorization parameters for Canva OAuth."""
    # Generate code verifier and challenge if not provided
    if code_challenge is None:
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        # Store code_verifier in oauth_config for later use
        oauth_config["code_verifier"] = code_verifier
        state = secrets.token_urlsafe(32)
    else:
        state = secrets.token_urlsafe(32)

    params = {
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
        "response_type": "code",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    return params


def build_canva_token_data(
    oauth_config: Dict[str, Any],
    redirect_uri: str,
    code: str,
    code_verifier: str = None,
) -> Dict[str, str]:
    """Build the token request data for Canva OAuth."""
    # Use the code_verifier from oauth_config if not provided
    if code_verifier is None:
        code_verifier = oauth_config.get("code_verifier")
        if not code_verifier:
            raise ValueError("code_verifier is required for token exchange")

    data = {
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
        "code": code,
        "redirect_uri": redirect_uri,
    }

    return data


def build_canva_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """Build the token request headers for Canva OAuth."""
    # Create Basic Auth credentials
    credentials = f"{oauth_config.get('client_id')}:{oauth_config.get('client_secret')}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    return {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def process_canva_token_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the token response from Canva OAuth."""
    # Handle both string and dict responses
    if isinstance(response_data, str):
        # Clean up XSSI prefix if present
        if response_data.startswith(")]}'"):
            response_data = response_data.split("\n", 1)[1]
        try:
            response_data = json.loads(response_data)
        except json.JSONDecodeError:
            # If it's not valid JSON, try to extract JSON from the string
            import re

            json_match = re.search(r"({.*})", response_data)
            if json_match:
                response_data = json.loads(json_match.group(1))
            else:
                raise ValueError(f"Invalid response format: {response_data}")

    # Handle error responses
    if "error" in response_data:
        error_msg = response_data.get(
            "error_description", response_data.get("error", "Unknown error")
        )
        raise ValueError(f"Token exchange failed: {error_msg}")

    # Validate required fields
    required_fields = ["access_token", "refresh_token", "expires_in"]
    missing_fields = [field for field in required_fields if field not in response_data]
    if missing_fields:
        raise ValueError(
            f"Missing required fields in token response: {', '.join(missing_fields)}"
        )

    return {
        "access_token": response_data.get("access_token"),
        "refresh_token": response_data.get("refresh_token"),
        "expires_in": response_data.get("expires_in"),
        "token_type": response_data.get("token_type"),
        "scope": response_data.get("scope"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Canva and save credentials"""
    # Generate PKCE values
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=CANVA_OAUTH_AUTHORIZE_URL,
        token_url=CANVA_OAUTH_TOKEN_URL,
        auth_params_builder=lambda oauth_config, redirect_uri, scopes: build_canva_auth_params(
            oauth_config, redirect_uri, scopes, code_challenge
        ),
        token_data_builder=lambda oauth_config, redirect_uri, scopes, code: build_canva_token_data(
            oauth_config, redirect_uri, code, code_verifier
        ),
        token_header_builder=build_canva_token_headers,
        process_token_response=process_canva_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Canva credentials (access token)"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=CANVA_OAUTH_TOKEN_URL,
        token_data_builder=build_canva_token_data,
        token_header_builder=build_canva_token_headers,
        process_token_response=process_canva_token_response,
        api_key=api_key,
    )
