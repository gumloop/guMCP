import json
import requests
import base64
from src.auth.factory import create_auth_client

def authenticate_and_save_credentials(user_id, service_name, scopes=None):
    """
    Run OAuth flow for Notion, using the client ID/secret loaded from auth_client's config,
    then save the token using the same auth_client.
    """
    auth_client = create_auth_client()

    # Load OAuth config for Notion
    oauth_config = auth_client.get_oauth_config(service_name)
    client_id = oauth_config["client_id"]
    client_secret = oauth_config["client_secret"]
    redirect_uri = oauth_config["redirect_uri"]

    # Step 1: Ask user to visit auth URL
    print("Visit this URL to authorize access:")
    auth_url = (
        f"https://api.notion.com/v1/oauth/authorize"
        f"?client_id={client_id}&response_type=code&owner=user&redirect_uri={redirect_uri}"
    )
    print(auth_url)

    # Step 2: Ask user to paste code
    code = input("Paste the code from the URL: ").strip()

    # Step 3: Exchange code for token
    headers = {
        "Authorization": "Basic " + base64.b64encode(
            f"{client_id}:{client_secret}".encode()
        ).decode(),
        "Content-Type": "application/json",
    }

    response = requests.post(
        "https://api.notion.com/v1/oauth/token",
        headers=headers,
        json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )

    data = response.json()

    if "access_token" not in data:
        raise Exception("OAuth failed", data)

    # Step 4: Save token using auth_client
    auth_client.save_user_credentials(service_name, user_id, data)
    print("✅ Authorization successful. Token saved for user:", user_id)
