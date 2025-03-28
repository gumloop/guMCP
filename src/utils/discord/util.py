import os
import logging
import time
import requests
import threading
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

from src.auth.factory import create_auth_client


DISCORD_OAUTH_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"


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
            print(f"RECEIVED AUTH CODE {self.server.auth_code}")
            success_message = "Authentication successful! You can close this window."
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
        <head><title>Discord Authentication</title></head>
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


def authenticate_and_save_credentials(user_id, service_name, scopes):
    """Authenticate with Discord and save credentials"""
    logger = logging.getLogger(service_name)

    logger.info(f"Launching auth flow for user {user_id}...")

    # Get auth client
    auth_client = create_auth_client()

    # Get OAuth config
    oauth_config = auth_client.get_oauth_config(service_name)

    client_id = oauth_config.get("client_id")
    client_secret = oauth_config.get("client_secret")
    redirect_uri = oauth_config.get("redirect_uri", "http://localhost:8080/callback")

    if not client_id or not client_secret:
        raise ValueError("Missing client_id or client_secret in OAuth config")

    # Create local server for callback
    server = HTTPServer(("localhost", 8080), OAuthCallbackHandler)
    server.auth_code = None
    server.auth_error = None

    # Start server in a thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # Build authorization URL
    scope_string = " ".join(scopes)
    auth_url = (
        f"{DISCORD_OAUTH_AUTHORIZE_URL}"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={urllib.parse.quote(scope_string)}"
    )

    # Open browser for authentication
    logger.info(f"Opening browser for OAuth flow...")
    webbrowser.open(auth_url)

    # Wait for callback (timeout after 120 seconds)
    max_wait_time = 120
    wait_time = 0
    while not server.auth_code and not server.auth_error and wait_time < max_wait_time:
        print("SERVER AUTH CODE: ", server.auth_code)
        print("SERVER AUTH ERROR: ", server.auth_error)
        time.sleep(1)
        wait_time += 1

    # Stop the server - improved shutdown process
    server.shutdown()
    server.server_close()  # Add this to close the socket immediately
    server_thread.join(timeout=5)  # Add timeout to prevent hanging

    if server.auth_error:
        logger.error(f"Authentication error: {server.auth_error}")
        raise ValueError(f"Authentication failed: {server.auth_error}")

    if not server.auth_code:
        logger.error("No authentication code received")
        raise ValueError("Authentication timed out or was canceled")

    # Exchange code for token
    print("EXCHANGING SERVER AUTH CODE: ", server.auth_code)
    logger.info("Exchanging authorization code for access token...")
    token_request_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": server.auth_code,
        "redirect_uri": redirect_uri,
    }

    print("TOKEN REQUEST DATA: ", token_request_data)
    token_response = requests.post(DISCORD_OAUTH_TOKEN_URL, data=token_request_data)
    print("TOKEN RESPONSE: ", token_response)
    if not token_response.ok:
        error_message = token_response.text
        logger.error(f"Token exchange failed: {error_message}")
        raise ValueError(f"Token exchange failed: {error_message}")

    token_data = token_response.json()

    # Add expiration timestamp
    if "expires_in" in token_data:
        token_data["expires_at"] = time.time() + token_data["expires_in"]

    logger.info(f"Token data: {token_data}")
    # Save credentials using auth client
    auth_client.save_user_credentials(service_name, user_id, token_data)

    logger.info(f"Credentials saved for user {user_id}. You can now run the server.")
    return token_data


async def get_credentials(user_id, service_name, api_key=None):
    """Get credentials for the specified user"""
    logger = logging.getLogger(service_name)

    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    token = auth_client.get_user_credentials(service_name, user_id)

    if not token:
        error_str = f"Credentials not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run with 'auth' argument first."
        logging.error(error_str)
        raise ValueError(error_str)

    # Check if token needs refresh
    if (
        "refresh_token" in token
        and "expires_at" in token
        and time.time() > token["expires_at"]
    ):
        try:
            # Get OAuth config
            oauth_config = auth_client.get_oauth_config(service_name)
            client_id = oauth_config.get("client_id")
            client_secret = oauth_config.get("client_secret")

            # Refresh the token
            refresh_data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": token["refresh_token"],
            }

            refresh_response = requests.post(DISCORD_OAUTH_TOKEN_URL, data=refresh_data)

            if refresh_response.ok:
                new_token = refresh_response.json()

                # Add expires_at if not present
                if "expires_in" in new_token:
                    new_token["expires_at"] = time.time() + new_token["expires_in"]

                # Save the refreshed token
                auth_client.save_user_credentials(service_name, user_id, new_token)
                return new_token
            else:
                logger.error(f"Failed to refresh token: {refresh_response.text}")
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            # Continue with existing token

    return token
