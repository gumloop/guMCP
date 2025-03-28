import os
import logging
import time
import webbrowser
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError

from src.auth.factory import create_auth_client

# Discord OAuth URLs
DISCORD_OAUTH_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_BASE_URL = "https://discord.com/api"

def authenticate_and_save_credentials(user_id, service_name, scopes):
    """Authenticate with Discord using OAuth2 and save credentials"""
    logger = logging.getLogger(service_name)
    logger.info(f"Launching auth flow for user {user_id}...")

    # Allow OAuth over HTTP for localhost (development only)
    if "localhost" in os.environ.get("OAUTH_REDIRECT_URI", "localhost"):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        logger.warning("OAuth insecure transport enabled for localhost development")

    # Get auth client
    auth_client = create_auth_client()

    # Get OAuth config
    oauth_config = auth_client.get_oauth_config(service_name)
    client_id = oauth_config.get("client_id")
    client_secret = oauth_config.get("client_secret")
    redirect_uri = oauth_config.get("redirect_uri", "http://localhost:8080/callback")

    if not client_id or not client_secret:
        raise ValueError("Missing client_id or client_secret in OAuth config")

    # Create OAuth session
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes)
    
    # Get authorization URL
    authorization_url, state = oauth.authorization_url(DISCORD_OAUTH_AUTHORIZE_URL)
    
    # Open browser for authentication
    logger.info(f"Opening browser for OAuth flow...")
    webbrowser.open(authorization_url)
    
    # Get the authorization response from user
    print("\nPlease authorize the application and paste the full callback URL here:")
    authorization_response = input().strip()
    
    try:
        # Fetch the token
        token = oauth.fetch_token(
            DISCORD_OAUTH_TOKEN_URL,
            authorization_response=authorization_response,
            client_secret=client_secret
        )
        
        # Add expiration timestamp
        if "expires_in" in token:
            token["expires_at"] = time.time() + token["expires_in"]
        
        # Save credentials using auth client
        auth_client.save_user_credentials(service_name, user_id, token)
        
        logger.info(f"Credentials saved for user {user_id}. You can now run the server.")
        return token
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise

async def get_credentials(user_id, service_name, api_key=None):
    """Get credentials for the specified user, refreshing if necessary"""
    logger = logging.getLogger(service_name)

    # Allow OAuth over HTTP for localhost (development only)
    if "localhost" in os.environ.get("OAUTH_REDIRECT_URI", "localhost"):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

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
    if "refresh_token" in token and "expires_at" in token and time.time() > token["expires_at"]:
        try:
            # Get OAuth config
            oauth_config = auth_client.get_oauth_config(service_name)
            client_id = oauth_config.get("client_id")
            client_secret = oauth_config.get("client_secret")
            
            # Set up refresh parameters
            refresh_kwargs = {
                "client_id": client_id,
                "client_secret": client_secret,
            }
            
            # Create OAuth session with token
            oauth = OAuth2Session(client_id, token=token)
            
            # Refresh the token
            new_token = oauth.refresh_token(DISCORD_OAUTH_TOKEN_URL, **refresh_kwargs)
            
            # Add expires_at if not present
            if "expires_in" in new_token:
                new_token["expires_at"] = time.time() + new_token["expires_in"]
            
            # Save the refreshed token
            auth_client.save_user_credentials(service_name, user_id, new_token)
            return new_token
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            # Continue with existing token

    return token