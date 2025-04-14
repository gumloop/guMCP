import os
import logging
import json
import requests
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

from src.auth.factory import create_auth_client


# Simple callback handler to capture the authorization code
class OAuthCallbackHandler(BaseHTTPRequestHandler):
    auth_code = None

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_path.query)
        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"<h1>Authorization successful!</h1>You can close this tab."
            )
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing authorization code")

    def log_message(self, format, *args):
        return  # Silence logs


def start_local_server(port):
    server = HTTPServer(("localhost", port), OAuthCallbackHandler)
    thread = Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server


def authenticate_and_save_credentials(user_id, service_name):
    """Authenticate with Zoom and save credentials automatically"""
    logger = logging.getLogger(service_name)
    logger.info(f"Launching auth flow for user {user_id}...")

    auth_client = create_auth_client()
    oauth_config = auth_client.get_oauth_config(service_name)

    client_id = oauth_config["client_id"]
    client_secret = oauth_config["client_secret"]
    auth_uri = oauth_config.get("auth_uri", "https://zoom.us/oauth/authorize")
    token_uri = oauth_config.get("token_uri", "https://zoom.us/oauth/token")
    redirect_uri = oauth_config.get(
        "redirect_uris", ["http://localhost:8080/callback"]
    )[0]

    # Start local server to receive auth code
    parsed_redirect = urllib.parse.urlparse(redirect_uri)
    port = parsed_redirect.port or 80
    server = start_local_server(port)

    # Build authorization URL
    auth_url = (
        f"{auth_uri}?response_type=code&client_id={client_id}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
    )

    logger.info(f"Opening browser for auth: {auth_url}")
    webbrowser.open(auth_url)

    print(f"Waiting for OAuth callback on {redirect_uri}...")

    # Wait until we get the code
    while OAuthCallbackHandler.auth_code is None:
        pass  # Busy wait

    server.shutdown()
    auth_code = OAuthCallbackHandler.auth_code

    # Exchange code for token
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }

    response = requests.post(
        token_uri,
        auth=(client_id, client_secret),
        data=token_data,
    )

    if response.status_code == 200:
        token = response.json()
        auth_client.save_user_credentials(service_name, user_id, token)

        logger.info(f"Credentials saved for user {user_id}.")
        print("✅ Authentication successful! Credentials saved.")
        return token
    else:
        logger.error(f"Token exchange failed: {response.text}")
        raise ValueError(f"Failed to obtain access token: {response.text}")
