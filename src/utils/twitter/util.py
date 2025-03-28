import os
import sys

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
import tweepy
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from src.auth.factory import create_auth_client


class TwitterCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Twitter OAuth callback."""

    def do_GET(self):
        """Handle GET request with OAuth callback."""
        # Skip favicon requests
        if self.path == "/favicon.ico":
            self.send_response(204)  # No Content
            self.end_headers()
            return

        # Twitter OAuth 1.0a uses oauth_verifier
        if "oauth_verifier" in self.path:
            self.server.oauth_verifier = self.path.split("oauth_verifier=")[1].split(
                "&"
            )[0]
            success_message = "Authentication successful! You can close this window."
        else:
            self.server.auth_error = "No oauth_verifier received"
            success_message = "Authentication failed. You can close this window."

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        response = f"""
        <html>
        <head><title>Twitter OAuth Authentication</title></head>
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


def authenticate_and_save_credentials(user_id, service_name):
    """Authenticate with Twitter and save credentials using OAuth 1.0a"""
    logger = logging.getLogger(service_name)

    logger.info(f"Launching auth flow for user {user_id}...")

    # Get auth client
    auth_client = create_auth_client()

    # Get OAuth config
    oauth_config = auth_client.get_oauth_config(service_name)
    consumer_key = oauth_config.get("consumer_key")
    consumer_secret = oauth_config.get("consumer_secret")

    if not consumer_key or not consumer_secret:
        raise ValueError(f"Missing OAuth credentials for {service_name}")

    # Create OAuth handler
    auth = tweepy.OAuth1UserHandler(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        callback="http://localhost:8080",
    )

    # Get request token and authorization URL
    try:
        redirect_url = auth.get_authorization_url()
    except Exception as e:
        logger.error(f"Error getting authorization URL: {str(e)}")
        raise

    # Set up server to receive callback
    server = HTTPServer(("localhost", 8080), TwitterCallbackHandler)
    server.oauth_verifier = None
    server.auth_error = None

    # Start server in a thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    print(f"\n===== Twitter Authentication =====")
    print(f"Opening browser for authentication...")

    # Open browser for user authorization
    webbrowser.open(redirect_url)

    # Wait for callback (timeout after 120 seconds)
    max_wait_time = 120
    wait_time = 0
    while (
        not server.oauth_verifier
        and not server.auth_error
        and wait_time < max_wait_time
    ):
        import time

        time.sleep(1)
        wait_time += 1

    # Stop the server
    server.shutdown()
    server_thread.join()

    if server.auth_error:
        logger.error(f"Authentication error: {server.auth_error}")
        raise ValueError(f"Authentication failed: {server.auth_error}")

    if not server.oauth_verifier:
        logger.error("No authentication verifier received")
        raise ValueError("Authentication timed out or was canceled")

    # Get access token with the verifier
    try:
        auth.request_token = auth.request_token
        auth.get_access_token(server.oauth_verifier)
        access_token = auth.access_token
        access_token_secret = auth.access_token_secret
    except Exception as e:
        logger.error(f"Error getting access token: {str(e)}")
        raise

    # Save credentials
    credentials = {
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret,
        "access_token": access_token,
        "access_token_secret": access_token_secret,
    }

    # Save credentials using auth client
    auth_client.save_user_credentials(service_name, user_id, credentials)

    logger.info(f"Credentials saved for user {user_id}. You can now run the server.")
    return credentials


async def get_credentials(user_id, service_name, api_key=None, api_secret=None):
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

    # For OAuth 1.0a, we need consumer key/secret and access token/secret
    required_keys = [
        "consumer_key",
        "consumer_secret",
        "access_token",
        "access_token_secret",
    ]

    # Ensure all required keys are present
    for key in required_keys:
        if key not in credentials_data:
            handle_missing_credentials()

    # Override consumer key/secret if provided
    if api_key and api_secret:
        credentials_data["consumer_key"] = api_key
        credentials_data["consumer_secret"] = api_secret

    return credentials_data
