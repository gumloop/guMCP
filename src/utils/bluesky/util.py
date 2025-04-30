import logging
import requests
import time
import jwt
from src.auth.factory import create_auth_client

logger = logging.getLogger(__name__)

# Bluesky API endpoints
BLUESKY_SESSION_URL = "https://bsky.social/xrpc/com.atproto.server.createSession"
BLUESKY_REFRESH_URL = "https://bsky.social/xrpc/com.atproto.server.refreshSession"


def get_credentials(user_id: str, api_key: str, service_name: str) -> dict:
    auth_client = create_auth_client(api_key=api_key)
    credentials = auth_client.get_user_credentials(service_name, user_id)

    if not credentials or "accessJwt" not in credentials:
        raise ValueError(
            f"Bluesky credentials not found for user {user_id}. Run 'auth' first."
        )

    # Decode JWT to get expiration time
    try:
        decoded_token = jwt.decode(
            credentials["accessJwt"], options={"verify_signature": False}
        )
        expires_at = decoded_token.get("exp")
    except jwt.DecodeError:
        logger.warning("Failed to decode JWT token, assuming token is expired")
        expires_at = 0

    # Check if token needs refresh
    if not expires_at or time.time() > expires_at - 300:  # 5 minutes buffer
        logger.info("Refreshing Bluesky token for user %s...", user_id)
        refresh_token = credentials.get("refreshJwt")
        if not refresh_token:
            raise ValueError("No refresh token available")

        headers = {
            "Authorization": f"Bearer {refresh_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(BLUESKY_REFRESH_URL, headers=headers)
        if response.status_code != 200:
            raise Exception(
                f"Token refresh failed: {response.status_code} - {response.text}"
            )

        refreshed_data = response.json()

        # Update stored credentials
        credentials.update(
            {
                "accessJwt": refreshed_data["accessJwt"],
                "refreshJwt": refreshed_data["refreshJwt"],
            }
        )

        # Save the updated credentials
        auth_client.save_user_credentials(service_name, user_id, credentials)
        logger.info("Token refreshed for user %s", user_id)

    credentials_data = {
        "accessJwt": credentials["accessJwt"],
        "refreshJwt": credentials["refreshJwt"],
        "handle": credentials["handle"],
        "did": credentials["did"],
    }

    return credentials_data


def authenticate_and_save_credentials(user_id: str, service_name: str):
    logger.info("Starting Bluesky authentication for user %s...", user_id)
    auth_client = create_auth_client()

    handle = input("Enter your Bluesky handle (e.g. you.bsky.social): ").strip()
    app_password = input("Enter your app password: ").strip()

    if not handle or not app_password:
        raise ValueError("Handle and app password are required")

    payload = {
        "identifier": handle,
        "password": app_password,
    }

    response = requests.post(BLUESKY_SESSION_URL, json=payload)

    if response.status_code != 200:
        raise Exception(
            f"Bluesky authentication failed: {response.status_code} - {response.text}"
        )

    session_data = response.json()
    auth_client.save_user_credentials(service_name, user_id, session_data)
    logger.info("Bluesky credentials saved for user %s", user_id)

    return session_data
