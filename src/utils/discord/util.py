import os
import logging
import time
import requests
import threading
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Any

from src.auth.factory import create_auth_client
from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed


DISCORD_OAUTH_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"

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


def build_discord_auth_params(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str]
) -> Dict[str, str]:
    """Build the authorization parameters for Discord OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
    }


def build_discord_token_data(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: List[str], auth_code: str
) -> Dict[str, str]:
    """Build the token request data for Discord OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }


def build_discord_refresh_data(
    oauth_config: Dict[str, Any], refresh_token: str, credentials: Dict[str, Any]
) -> Dict[str, str]:
    """Build the token refresh data for Discord OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "client_secret": oauth_config.get("client_secret"),
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Authenticate with Discord and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=DISCORD_OAUTH_AUTHORIZE_URL,
        token_url=DISCORD_OAUTH_TOKEN_URL,
        auth_params_builder=build_discord_auth_params,
        token_data_builder=build_discord_token_data,
    )


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Discord credentials"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=DISCORD_OAUTH_TOKEN_URL,
        token_data_builder=build_discord_refresh_data,
        api_key=api_key,
    )
