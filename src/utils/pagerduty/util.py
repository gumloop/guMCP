import logging
from typing import Dict, List, Any
import json

from src.utils.oauth.util import (
    run_oauth_flow,
    refresh_token_if_needed,
    generate_code_verifier,
    generate_code_challenge,
)


PAGERDUTY_OAUTH_AUTHORIZE_URL = "https://app.pagerduty.com/oauth/authorize"
PAGERDUTY_OAUTH_TOKEN_URL = "https://app.pagerduty.com/oauth/token"
PAGERDUTY_API_URL = "https://api.pagerduty.com"

logger = logging.getLogger(__name__)


def build_pagerduty_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    code_challenge = oauth_config.get("code_challenge", "")
    state = oauth_config.get("state", "")

    params = {
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
    }

    if state:
        params["state"] = state
    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

    return params


def build_pagerduty_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    token_data = {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    if oauth_config.get("code_verifier"):
        token_data["code_verifier"] = oauth_config.get("code_verifier")

    return token_data


def process_pagerduty_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    if not token_response.get("access_token"):
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}"
        )

    access_token = token_response.get("access_token")

    return {
        "access_token": access_token,
        "token_type": token_response.get("token_type", "Bearer"),
        "refresh_token": token_response.get("refresh_token"),
        "scope": token_response.get("scope", ""),
        "expires_in": token_response.get("expires_in"),
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    state_data = {"code_verifier": code_verifier}
    state = json.dumps(state_data)

    from src.auth.factory import create_auth_client

    auth_client = create_auth_client()
    oauth_config = auth_client.get_oauth_config(service_name)

    oauth_config["code_verifier"] = code_verifier
    oauth_config["code_challenge"] = code_challenge
    oauth_config["state"] = state

    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=PAGERDUTY_OAUTH_AUTHORIZE_URL,
        token_url=PAGERDUTY_OAUTH_TOKEN_URL,
        auth_params_builder=build_pagerduty_auth_params,
        token_data_builder=build_pagerduty_token_data,
        process_token_response=process_pagerduty_token_response,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=PAGERDUTY_OAUTH_TOKEN_URL,
        token_data_builder=build_pagerduty_token_data,
        api_key=api_key,
    )
