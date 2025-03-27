import abc
from typing import Dict, Any, Optional, TypeVar, Generic

# Generic type to represent any type of credentials object
CredentialsT = TypeVar("CredentialsT")


class BaseAuthClient(Generic[CredentialsT], abc.ABC):
    """
    Abstract base class for authentication clients.
    Generic auth client that can work with any API authentication system.
    """

    @abc.abstractmethod
    def get_user_credentials(
        self, service_name: str, user_id: str
    ) -> Optional[CredentialsT]:
        """
        Retrieves user credentials for a specific service. Credentials returned here should be ready-to-use (ex. access tokens should be refreshed already)

        Args:
            service_name: Name of the service (e.g., "gdrive", "github", etc.)
            user_id: Identifier for the user

        Returns:
            Credentials object if found, None otherwise
        """
        pass

    def get_oauth_config(self, service_name: str) -> Dict[str, Any]:
        """
        Retrieves OAuth configuration for a specific service

        Args:
            service_name: Name of the service (e.g., "gdrive", "github", etc.)

        Returns:
            Dict containing OAuth configuration
        """
        raise NotImplementedError(
            "This method is optional and not implemented by this client"
        )

    def save_user_credentials(
        self, service_name: str, user_id: str, credentials: CredentialsT
    ) -> None:
        """
        Saves user credentials after authentication or refresh

        Args:
            service_name: Name of the service (e.g., "gdrive", "github", etc.)
            user_id: Identifier for the user
            credentials: Credentials object to save
        """
        raise NotImplementedError(
            "This method is optional and not implemented by this client"
        )
