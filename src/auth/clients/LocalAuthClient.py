import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union

from .BaseAuthClient import BaseAuthClient, CredentialsT

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("LocalAuthClient")


class LocalAuthClient(BaseAuthClient[CredentialsT]):
    """
    Implementation of BaseAuthClient that reads/writes credentials to local files.
    Useful for local development and self-hosted installations.

    Can work with any type of credentials object that can be serialized to/from JSON.
    """

    def __init__(
        self,
        oauth_config_base_dir: Optional[str] = None,
        credentials_base_dir: Optional[str] = None,
    ):
        """
        Initialize the local file auth client

        Args:
            oauth_config_base_dir: Directory containing OAuth config files
            credentials_base_dir: Base directory to store user credentials
        """
        # Get the project root directory (GuMCP/)
        project_root = Path(__file__).parent.parent.parent.parent

        print(f"Using project root: {project_root}")

        self.oauth_config_base_dir = oauth_config_base_dir or os.environ.get(
            "GUMCP_OAUTH_CONFIG_DIR", str(project_root / "local_auth" / "oauth_configs")
        )

        self.credentials_base_dir = credentials_base_dir or os.environ.get(
            "GUMCP_CREDENTIALS_DIR", str(project_root / "local_auth" / "credentials")
        )

        # Ensure directories exist
        if self.oauth_config_base_dir:
            os.makedirs(self.oauth_config_base_dir, exist_ok=True)
        if self.credentials_base_dir:
            os.makedirs(self.credentials_base_dir, exist_ok=True)

    def get_oauth_config(self, service_name: str) -> Dict[str, Any]:
        """Retrieve OAuth configuration from local file"""
        if not self.oauth_config_base_dir:
            raise ValueError("OAuth config directory not set")

        service_dir = os.path.join(self.oauth_config_base_dir, service_name)
        os.makedirs(service_dir, exist_ok=True)

        config_path = os.path.join(service_dir, "oauth.json")

        print("config_path:" + config_path)

        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"OAuth config not found for {service_name} at {config_path}"
            )

        with open(config_path, "r") as f:
            return json.load(f)

    def get_user_credentials(
        self, service_name: str, user_id: str
    ) -> Optional[CredentialsT]:
        """Retrieve user credentials from local file"""
        if not self.credentials_base_dir:
            raise ValueError("Credentials directory not set")

        service_dir = os.path.join(self.credentials_base_dir, service_name)
        os.makedirs(service_dir, exist_ok=True)

        creds_path = os.path.join(service_dir, f"{user_id}_credentials.json")

        print("creds_path:" + creds_path)

        if not os.path.exists(creds_path):
            return None

        with open(creds_path, "r") as f:
            credentials_data = json.load(f)

        # The caller is responsible for converting JSON to the appropriate credentials type
        return credentials_data

    def save_user_credentials(
        self,
        service_name: str,
        user_id: str,
        credentials: Union[CredentialsT, Dict[str, Any]],
    ) -> None:
        """Save user credentials to local file"""
        if not self.credentials_base_dir:
            raise ValueError("Credentials directory not set")

        service_dir = os.path.join(self.credentials_base_dir, service_name)
        os.makedirs(service_dir, exist_ok=True)

        creds_path = os.path.join(service_dir, f"{user_id}_credentials.json")

        # Handle different credential types
        if hasattr(credentials, "to_json"):
            # If credentials object has a to_json method, use it
            credentials_json = credentials.to_json()
        elif isinstance(credentials, dict):
            # If credentials is already a dict, serialize it
            credentials_json = json.dumps(credentials)
        else:
            # Try to serialize the object directly
            credentials_json = json.dumps(credentials)

        with open(creds_path, "w") as f:
            f.write(credentials_json)
