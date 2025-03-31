from typing import Dict, Any

import time
import base64
import logging

from src.auth.factory import create_auth_client
from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUICKBOOKS_OAUTH_AUTHORIZE_URL = "https://appcenter.intuit.com/connect/oauth2"
QUICKBOOKS_OAUTH_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"


def build_quickbooks_auth_params(
    oauth_config: dict, redirect_uri: str, scopes: list[str]
) -> dict:
    """Build the authorization parameters for QuickBooks OAuth."""
    return {
        "client_id": oauth_config.get("client_id"),
        "scope": " ".join(scopes),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": "state",
    }


def build_quickbooks_token_headers(oauth_config: Dict[str, Any]) -> Dict[str, str]:
    """Build the token request headers for Quickbooks OAuth."""
    # Concatenate client_id and client_secret with a colon
    credentials = f'{oauth_config.get("client_id")}:{oauth_config.get("client_secret")}'

    # Encode the credentials in base64 format
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}",
    }


def build_quickbooks_token_data(
    oauth_config: dict, redirect_uri: str, scopes: list[str], auth_code: str
) -> dict:
    """Build the token request data for QuickBooks OAuth."""
    return {
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }


def process_quickbooks_token_response(token_response: dict) -> dict:
    """Process QuickBooks token response."""
    if "error" in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error_description', 'Unknown error')}"
        )

    # Store credentials with additional QuickBooks-specific fields
    return {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_in": token_response.get("expires_in", 3600),
        "expires_at": int(time.time()) + token_response.get("expires_in", 3600),
        "realmId": token_response.get("realmId"),
    }


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """Get Quickbooks credentials"""
    return await refresh_token_if_needed(
        user_id=user_id,
        service_name=service_name,
        token_url=QUICKBOOKS_OAUTH_TOKEN_URL,
        token_data_builder=lambda _, refresh_token, __: {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        token_header_builder=build_quickbooks_token_headers,
        api_key=api_key,
        return_full_credentials=True,
    )


def authenticate_and_save_credentials(
    user_id: str, service_name: str, scopes: list[str]
) -> dict:
    """Authenticate with QuickBooks and save credentials"""

    # QuickBooks OAuth endpoints
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=QUICKBOOKS_OAUTH_AUTHORIZE_URL,
        token_url=QUICKBOOKS_OAUTH_TOKEN_URL,
        auth_params_builder=build_quickbooks_auth_params,
        token_data_builder=build_quickbooks_token_data,
        token_header_builder=build_quickbooks_token_headers,
        process_token_response=process_quickbooks_token_response,
    )


# Formatters


def format_customer(customer):
    """Format a QuickBooks customer object for display"""
    return {
        "id": customer.Id,
        "display_name": customer.DisplayName,
        "company_name": getattr(customer, "CompanyName", ""),
        "email": (
            getattr(customer.PrimaryEmailAddr, "Address", "")
            if hasattr(customer, "PrimaryEmailAddr")
            else ""
        ),
        "phone": (
            getattr(customer.PrimaryPhone, "FreeFormNumber", "")
            if hasattr(customer, "PrimaryPhone")
            else ""
        ),
        "balance": getattr(customer, "Balance", 0),
    }


def format_invoice(invoice):
    """Format a QuickBooks invoice for display"""
    return {
        "id": invoice.Id,
        "doc_number": getattr(invoice, "DocNumber", ""),
        "customer": (
            getattr(invoice.CustomerRef, "name", "")
            if hasattr(invoice, "CustomerRef")
            else ""
        ),
        "date": getattr(invoice, "TxnDate", ""),
        "due_date": getattr(invoice, "DueDate", ""),
        "total": getattr(invoice, "TotalAmt", 0),
        "balance": getattr(invoice, "Balance", 0),
        "status": "Paid" if getattr(invoice, "Balance", 0) == 0 else "Outstanding",
    }


def format_account(account):
    """Format a QuickBooks account for display"""
    return {
        "id": account.Id,
        "name": account.Name,
        "account_type": account.AccountType,
        "account_sub_type": getattr(account, "AccountSubType", ""),
        "current_balance": getattr(account, "CurrentBalance", 0),
    }
