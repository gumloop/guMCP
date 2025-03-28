import os
import time
import logging
import requests
import threading
import webbrowser
import urllib.parse

from http.server import HTTPServer, BaseHTTPRequestHandler

from src.auth.factory import create_auth_client


X_OAUTH_AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
X_OAUTH_TOKEN_URL = "https://api.x.com/2/oauth2/token"
X_API_BASE = "https://api.x.com/2/"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    def __init__(self, *args, **kwargs):
        self.auth_code = None
        self.auth_error = None
        super().__init__(*args, **kwargs)

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
        <head><title>X Authentication</title></head>
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
    """Authenticate with X and save credentials"""
    logger = logging.getLogger(service_name)

    logger.info(f"Launching auth flow for user {user_id}...")

    # Get auth client
    auth_client = create_auth_client()

    # Get OAuth config
    oauth_config = auth_client.get_oauth_config(service_name)

    client_id = oauth_config.get("client_id")
    client_secret = oauth_config.get("client_secret")

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
    redirect_uri = oauth_config.get("redirect_uri")
    # X uses PKCE for OAuth 2.0
    code_verifier = os.urandom(32).hex()
    code_challenge = code_verifier  # In production, this should be hashed

    auth_url = (
        f"{X_OAUTH_AUTHORIZE_URL}"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope_string}"
        f"&response_type=code"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=plain"
        f"&state=state"
    )

    # Open browser for authentication
    logger.info(f"Opening browser for OAuth flow...")
    webbrowser.open(auth_url)

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

    # Exchange code for token
    logger.info("Exchanging authorization code for access token...")
    token_request_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": server.auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }

    token_response = requests.post(X_OAUTH_TOKEN_URL, data=token_request_data)
    token_data = token_response.json()

    if not token_response.ok:
        logger.error(
            f"Token exchange failed: {token_data.get('error', 'Unknown error')}"
        )
        raise ValueError(
            f"Token exchange failed: {token_data.get('error', 'Unknown error')}"
        )

    # Extract and prepare credentials
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    # Store credentials
    credentials = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_data.get("token_type", "Bearer"),
        "expires_in": token_data.get("expires_in"),
        "scope": token_data.get("scope", ""),
    }

    # Save credentials using auth client
    auth_client.save_user_credentials(service_name, user_id, credentials)

    logger.info(f"Credentials saved for user {user_id}. You can now run the server.")
    return credentials


async def get_credentials(user_id, service_name, api_key=None):
    """Get credentials for the specified user"""
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

    # For X, we just need the access token
    access_token = credentials_data.get("access_token")
    if access_token:
        return access_token

    handle_missing_credentials()
