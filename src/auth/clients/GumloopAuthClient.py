import os
import logging
import requests
from typing import Optional

from .BaseAuthClient import BaseAuthClient, CredentialsT

logger = logging.getLogger("gumloop-auth-client")


class GumloopAuthClient(BaseAuthClient[CredentialsT]):
    """
    Implementation of BaseAuthClient that uses Gumloop's infrastructure.

    Can work with any type of credentials that can be linked from https://gumloop.com/credentials
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gumloop auth client

        Args:
            api_key: Gumloop API key for service authentication
        """
        self.api_base_url = os.environ.get(
            "GUMLOOP_API_BASE_URL", "https://api.gumloop.com/api/v1"
        )
        self.api_key = api_key

        if not all([self.api_base_url, self.api_key]):
            logger.warning(
                "Missing configuration for GumloopAuthClient. Some functionality may be limited."
            )

    def get_user_credentials(
        self, service_name: str, user_id: str
    ) -> Optional[CredentialsT]:
        """Get user credentials from Gumloop API"""

        url = f"{self.api_base_url}/auth/{service_name}/credentials?user_id={user_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(
                    f"Failed to get credentials for {service_name} user {user_id}: {response.text}"
                )
                return None

            # Return the credentials data as a dictionary
            # The caller is responsible for converting to the appropriate credentials type
            return response.json()
        except Exception as e:
            logger.error(
                f"Error retrieving credentials for {service_name} user {user_id}: {str(e)}"
            )
            return None
