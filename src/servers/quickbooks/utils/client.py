import os
import sys
import logging
from intuitlib.client import AuthClient
from quickbooks import QuickBooks

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from src.utils.quickbooks.util import get_credentials

logger = logging.getLogger(__name__)

async def create_quickbooks_client(user_id: str) -> QuickBooks:
    """Create a QuickBooks client with stored credentials"""
    try:
        # Get credentials from storage
        credentials = await get_credentials(user_id, "quickbooks")
        
        # Create auth client
        auth_client = AuthClient(
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
            environment=credentials["environment"],
            redirect_uri=credentials["redirect_uri"]
        )
        
        # Set tokens
        auth_client.token = credentials["access_token"]
        
        # Create QuickBooks client
        client = QuickBooks(
            auth_client=auth_client,
            refresh_token=credentials["refresh_token"],
            company_id=credentials["realm_id"]
        )
        
        return client
        
    except Exception as e:
        logger.error(f"Error creating QuickBooks client: {e}")
        raise 