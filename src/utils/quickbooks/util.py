import json
import os
import logging
from pathlib import Path

from intuitlib.client import AuthClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_credentials(user_id: str, service_name: str, api_key=None) -> dict:
    """Get stored credentials for the user"""
    creds_dir = Path.home() / ".config" / "gumcp" / service_name
    creds_file = creds_dir / f"{user_id}.json"

    if not creds_file.exists():
        raise ValueError(
            f"No credentials found for user {user_id}. Please run authentication flow first."
        )

    with open(creds_file) as f:
        return json.load(f)


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: list[str]
) -> None:
    """Run OAuth flow and save credentials"""
    try:
        # Create config directory if it doesn't exist
        creds_dir = Path.home() / ".config" / "gumcp" / service_name
        creds_dir.mkdir(parents=True, exist_ok=True)

        # Get OAuth credentials from environment
        client_id = os.getenv("QUICKBOOKS_CLIENT_ID")
        client_secret = os.getenv("QUICKBOOKS_CLIENT_SECRET")
        redirect_uri = os.getenv(
            "QUICKBOOKS_REDIRECT_URI",
            "https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl",
        )
        environment = os.getenv("QUICKBOOKS_ENVIRONMENT", "sandbox")

        if not all([client_id, client_secret]):
            raise ValueError(
                "Missing required environment variables: QUICKBOOKS_CLIENT_ID, QUICKBOOKS_CLIENT_SECRET"
            )

        logger.info(f"Initializing auth client with environment: {environment}")

        # Initialize auth client
        auth_client = AuthClient(
            client_id=client_id,
            client_secret=client_secret,
            environment=environment,
            redirect_uri=redirect_uri,
        )

        # Get authorization URL
        auth_url = auth_client.get_authorization_url(scopes)
        print("\n=== QuickBooks Authentication ===")
        print("1. Visit this URL to authorize access:")
        print(f"\n{auth_url}\n")
        print("2. On the QuickBooks authorization page:")
        print("   - Log in to your QuickBooks account if needed")
        print("   - Review and approve the requested permissions")
        print("   - You will be redirected to the OAuth Playground")
        print("\n3. On the OAuth Playground page:")
        print("   - Look for the 'Authorization Code' field")
        print("   - Look for the 'Realm ID' field")
        print("   - Copy both values")
        print("\n4. Enter the values below:")

        # Get values from user
        auth_code = input("\nEnter the Authorization Code: ").strip()
        realm_id = input("Enter the Realm ID: ").strip()

        if not auth_code or not realm_id:
            raise ValueError("Both Authorization Code and Realm ID are required")

        print(f"\nFound QuickBooks company ID: {realm_id}")

        logger.info("Exchanging authorization code for tokens...")

        # Exchange auth code for tokens
        auth_client.get_bearer_token(auth_code, realm_id=realm_id)

        logger.info("Successfully obtained tokens")

        # Save credentials
        creds = {
            "client_id": client_id,
            "client_secret": client_secret,
            "access_token": auth_client.access_token,
            "refresh_token": auth_client.refresh_token,
            "realm_id": realm_id,
            "redirect_uri": redirect_uri,
            "environment": environment,
        }

        creds_file = creds_dir / f"{user_id}.json"
        with open(creds_file, "w") as f:
            json.dump(creds, f, indent=2)

        logger.info(f"Credentials saved to {creds_file}")
        print("\nAuthentication successful! Credentials have been saved.")

    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        print("\nAuthentication failed. Please try again.")
        print(
            "Make sure to copy both the Authorization Code and Realm ID from the OAuth Playground page."
        )
        raise
