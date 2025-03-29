import os
import sys
import logging
from intuitlib.client import AuthClient
from quickbooks import QuickBooks

# Add project root to Python path when running directly
if __name__ == "__main__":
    project_root = os.path.abspath(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    )
    sys.path.insert(0, project_root)

from src.utils.quickbooks.util import get_credentials

logger = logging.getLogger(__name__)

async def create_quickbooks_client(user_id: str) -> QuickBooks:
    """Create a QuickBooks client with stored credentials"""
    try:
        # Get stored credentials
        creds = await get_credentials(user_id, "quickbooks")
        if not creds:
            raise ValueError("No stored credentials found. Please run authentication first.")
            
        # Create auth client
        auth_client = AuthClient(
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            environment=creds["environment"],
            redirect_uri=creds["redirect_uri"]
        )
        
        # Set tokens
        auth_client.access_token = creds["access_token"]
        auth_client.refresh_token = creds["refresh_token"]
        auth_client.realm_id = creds["realm_id"]
        
        # Create QuickBooks client
        qb_client = QuickBooks(
            auth_client=auth_client,
            refresh_token=creds["refresh_token"],
            company_id=creds["realm_id"],
            environment=creds["environment"]
        )
        
        return qb_client
        
    except Exception as e:
        logger.error(f"Failed to create QuickBooks client: {str(e)}")
        raise 