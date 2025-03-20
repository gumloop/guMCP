import os
import logging
from typing import Dict, Any, Optional, Union

from google.cloud import secretmanager
from auth.clients.BaseAuthClient import BaseAuthClient, CredentialsT

logger = logging.getLogger("gumloop-auth-client")

class GumloopAuthClient(BaseAuthClient[CredentialsT]):
    """
    Implementation of BaseAuthClient that uses Gumloop's infrastructure.
    Gets OAuth config from GCP Secret Manager and user credentials from Gumloop's API.
    
    Can work with any type of credentials that can be serialized to/from JSON.
    """
    
    def __init__(self, 
                 gcp_project_id: str = None,
                 api_base_url: str = None,
                 api_key: str = None):
        """
        Initialize the Gumloop auth client
        
        Args:
            gcp_project_id: GCP project ID for Secret Manager
            api_base_url: Base URL for Gumloop API
            api_key: API key for internal service authentication
        """
        self.gcp_project_id = gcp_project_id or os.environ.get("GCP_PROJECT_ID")
        self.api_base_url = api_base_url or os.environ.get("GUMLOOP_API_BASE_URL", "https://api.gumloop.com")
        self.api_key = api_key or os.environ.get("GUMLOOP_API_KEY")
        
        # Initialize GCP Secret Manager client
        self.secret_client = secretmanager.SecretManagerServiceClient()
        
        if not all([self.gcp_project_id, self.api_base_url, self.api_key]):
            logger.warning("Missing configuration for GumloopAuthClient. Some functionality may be limited.")
    
    def get_oauth_config(self, service_name: str) -> Dict[str, Any]:
        """Retrieve OAuth configuration from GCP Secret Manager"""
        import json
        
        secret_name = f"{service_name}-oauth-config"
        secret_path = f"projects/{self.gcp_project_id}/secrets/{secret_name}/versions/latest"
        
        try:
            response = self.secret_client.access_secret_version(request={"name": secret_path})
            return json.loads(response.payload.data.decode("UTF-8"))
        except Exception as e:
            logger.error(f"Failed to retrieve OAuth config for {service_name}: {str(e)}")
            raise
    
    def get_user_credentials(self, service_name: str, user_id: str) -> Optional[CredentialsT]:
        """Get user credentials from Gumloop API"""
        import requests
        
        url = f"{self.api_base_url}/auth/{service_name}/{user_id}/credentials"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to get credentials for {service_name} user {user_id}: {response.text}")
                return None
            
            # Return the credentials data as a dictionary
            # The caller is responsible for converting to the appropriate credentials type
            return response.json()
        except Exception as e:
            logger.error(f"Error retrieving credentials for {service_name} user {user_id}: {str(e)}")
            return None
    
    def save_user_credentials(self, service_name: str, user_id: str, credentials: Union[CredentialsT, Dict[str, Any]]) -> None:
        """Save user credentials to Gumloop API"""
        import requests
        import json
        
        url = f"{self.api_base_url}/auth/{service_name}/{user_id}/credentials"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Handle different credential types
        if hasattr(credentials, 'to_json'):
            # If credentials object has a to_json method, use it
            credentials_json = json.loads(credentials.to_json())
        elif isinstance(credentials, dict):
            # If credentials is already a dict, use it directly
            credentials_json = credentials
        else:
            # Try to convert to dictionary directly
            credentials_json = credentials
        
        try:
            response = requests.post(url, headers=headers, json=credentials_json)
            
            if response.status_code not in (200, 201):
                logger.error(f"Failed to save credentials for {service_name} user {user_id}: {response.text}")
                raise RuntimeError(f"Failed to save credentials: {response.status_code}")
        except Exception as e:
            logger.error(f"Error saving credentials for {service_name} user {user_id}: {str(e)}")
            raise