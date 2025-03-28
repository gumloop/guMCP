import os
import json
import time
import base64
import hashlib
import secrets
import logging
import requests
import threading
import webbrowser
import urllib.parse

from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any, Callable

from src.auth.factory import create_auth_client


logger = logging.getLogger(__name__)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    def do_GET(self):
        """Handle GET request with OAuth callback."""
        # Skip favicon requests
        if self.path == "/favicon.ico":
            self.send_response(204)  # No Content
            self.end_headers()
            return

        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        if "code" in query_params:
            self.server.auth_code = query_params["code"][0]
            success_message = "Authentication successful! You can close this window."

            # Parse state if present to extract code_verifier
            if "state" in query_params:
                try:
                    state_json = query_params["state"][0]
                    state_data = json.loads(state_json)
                    if "code_verifier" in state_data:
                        self.server.code_verifier = state_data["code_verifier"]
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse state parameter: {e}")
        elif "error" in query_params:
            self.server.auth_error = query_params["error"][0]
            success_message = f"Authentication error: {self.server.auth_error}. You can close this window."
        else:
            self.server.auth_error = "No code or error received"
            success_message = "Authentication failed. You can close this window."

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        response = f"""
        <html>
        <head><title>OAuth Authentication</title></head>
        <body>
        <h1>{success_message}</h1>
        <script>
            setTimeout(function() {{
                window.close();
            }}, 3000);
        </script>
        </body>
        </html>
        """
        self.wfile.write(response.encode("utf-8"))


def run_oauth_flow(
    service_name: str,
    user_id: str,
    scopes: List[str],
    auth_url_base: str,
    token_url: str,
    auth_params_builder: Callable[[Dict[str, Any], str, List[str]], Dict[str, str]],
    token_data_builder: Callable[[Dict[str, Any], str, List[str], str], Dict[str, str]],
    process_token_response: Callable[[Dict[str, Any]], Dict[str, Any]] = None,
    token_header_builder: Callable[[Dict[str, Any]], Dict[str, str]] = None,
    port: int = 8080,
) -> Dict[str, Any]:
    """
    Generic OAuth flow handler that can be used by different services

    Args:
        service_name: Name of the service (e.g., 'microsoft', 'slack')
        user_id: ID of the user authenticating
        scopes: List of OAuth scopes to request
        auth_url_base: Base authorization URL for the service
        token_url: Token exchange URL for the service
        auth_params_builder: Function to build auth URL parameters
        token_data_builder: Function to build token request data
        process_token_response: Optional function to process token response
        token_header_builder: Optional function to build token request headers
        port: Port to use for local callback server

    Returns:
        Dict containing the OAuth credentials
    """
    logger = logging.getLogger(service_name)
    logger.info(f"Launching auth flow for user {user_id}...")

    # Get auth client
    auth_client = create_auth_client()

    # Get OAuth config
    oauth_config = auth_client.get_oauth_config(service_name)

    if not oauth_config.get("client_id") or not oauth_config.get("client_secret"):
        raise ValueError(f"Missing OAuth credentials for {service_name}")

    # Get redirect URI from config or use default
    redirect_uri = oauth_config.get("redirect_uri", f"http://localhost:{port}")

    # Create local server for callback
    server = HTTPServer(("localhost", port), OAuthCallbackHandler)
    server.auth_code = None
    server.auth_error = None

    # Start server in a thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # Build auth params and URL
    auth_params = auth_params_builder(oauth_config, redirect_uri, scopes)
    auth_request_url = f"{auth_url_base}?{urllib.parse.urlencode(auth_params)}"

    print(f"\n===== {service_name.title()} Authentication =====")
    print(f"Opening browser for authentication...")

    # Open the browser for authorization
    webbrowser.open(auth_request_url)

    # Wait for callback (timeout after 120 seconds)
    max_wait_time = 120
    wait_time = 0
    while not server.auth_code and not server.auth_error and wait_time < max_wait_time:
        time.sleep(1)
        wait_time += 1

    # Stop the server
    server.shutdown()
    server_thread.join()

    if server.auth_error:
        logger.error(f"Authentication error: {server.auth_error}")
        raise ValueError(f"Authentication failed: {server.auth_error}")

    if not server.auth_code:
        logger.error("No authentication code received")
        raise ValueError("Authentication timed out or was canceled")

    if hasattr(server, "code_verifier"):
        oauth_config["code_verifier"] = server.code_verifier

    # Exchange the authorization code for tokens
    token_data = token_data_builder(
        oauth_config,
        redirect_uri,
        scopes,
        server.auth_code,
    )

    # Add headers if header builder is provided
    headers = token_header_builder(oauth_config) if token_header_builder else None
    response = requests.post(token_url, data=token_data, headers=headers)
    if response.status_code != 200:
        raise ValueError(
            f"Failed to exchange authorization code for tokens: {response.text}"
        )

    token_response = response.json()

    # Process the token response if needed
    if process_token_response:
        token_response = process_token_response(token_response)
    else:
        # Default processing - add expiry time
        token_response["expires_at"] = int(time.time()) + token_response.get(
            "expires_in", 3600
        )

    # Save credentials using auth client
    auth_client.save_user_credentials(service_name, user_id, token_response)

    logger.info(f"Credentials saved for user {user_id}. You can now run the server.")
    return token_response


async def refresh_token_if_needed(
    user_id: str,
    service_name: str,
    token_url: str,
    token_data_builder: Callable[[Dict[str, Any], str, Dict[str, Any]], Dict[str, str]],
    process_token_response: Callable[[Dict[str, Any]], Dict[str, Any]] = None,
    token_header_builder: Callable[[Dict[str, Any]], Dict[str, str]] = None,
    api_key: Optional[str] = None,
) -> str:
    """
    Checks if token needs refresh and handles the refresh process

    Args:
        user_id: ID of the user
        service_name: Name of the service
        token_url: URL for token refresh
        token_data_builder: Function to build token refresh request data
        process_token_response: Optional function to process token response
        token_header_builder: Optional function to build token request headers
        api_key: Optional API key

    Returns:
        The current valid access token
    """
    logger = logging.getLogger(service_name)

    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials(service_name, user_id)

    def handle_missing_credentials():
        error_str = f"Credentials not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run with 'auth' argument first."
        logging.error(error_str)
        raise ValueError(f"Credentials not found for user {user_id}")

    if not credentials_data:
        handle_missing_credentials()

    # Check if the token has an expiration time (some don't)
    if (
        "expires_at" in credentials_data
        # Non-local OAuth clients expected to handle refreshing in get_user_credentials()
        and os.getenv("ENVIRONMENT", "local") == "local"
    ):
        # Check if we need to refresh the token
        expires_at = credentials_data.get("expires_at", 0)

        # Refresh if token is expired or will expire in the next 5 minutes
        if time.time() > expires_at - 300:  # 5 minutes buffer
            refresh_token = credentials_data.get("refresh_token")
            if not refresh_token:
                handle_missing_credentials()

            # Get OAuth config
            oauth_config = auth_client.get_oauth_config(service_name)

            # Build token refresh data
            token_data = token_data_builder(
                oauth_config, refresh_token, credentials_data
            )

            # Add headers if header builder is provided
            headers = (
                token_header_builder(oauth_config) if token_header_builder else None
            )
            response = requests.post(token_url, data=token_data, headers=headers)
            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.text}")
                handle_missing_credentials()

            new_credentials = response.json()

            # Process the token response if needed
            if process_token_response:
                new_credentials = process_token_response(new_credentials)
            else:
                # Default processing - add expiry time
                new_credentials["expires_at"] = int(time.time()) + new_credentials.get(
                    "expires_in", 3600
                )

            # Preserve refresh token if not returned (some services don't)
            if "refresh_token" not in new_credentials and refresh_token:
                new_credentials["refresh_token"] = refresh_token

            # Save the updated credentials
            auth_client.save_user_credentials(service_name, user_id, new_credentials)

            return new_credentials.get("access_token")

    return credentials_data.get("access_token")


def generate_code_verifier() -> str:
    """Generate a code verifier for PKCE.

    Creates a cryptographically secure random string between 43-128 characters
    using only a-z, A-Z, 0-9, ".", "-", and "_" characters.
    """
    # Generate a random string of 64 characters (reasonable middle value in the 43-128 range)
    allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._"
    code_verifier = "".join(secrets.choice(allowed_chars) for _ in range(64))
    return code_verifier


def generate_code_challenge(code_verifier: str) -> str:
    """Generate a code challenge from the code verifier.

    Creates a base64 url encoded SHA-256 hash of the code verifier
    with padding characters removed.
    """
    # Create SHA-256 hash
    code_challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()

    # Convert to base64 and make URL safe
    code_challenge = base64.urlsafe_b64encode(code_challenge_bytes).decode("utf-8")

    # Remove padding characters (=)
    return code_challenge.replace("=", "")
