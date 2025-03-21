import os
import logging
from typing import Optional, TypeVar, Type

from .clients.BaseAuthClient import BaseAuthClient

logger = logging.getLogger("auth-factory")

T = TypeVar("T", bound=BaseAuthClient)


def create_auth_client(
    client_type: Optional[Type[T]] = None, api_key: Optional[str] = None
) -> BaseAuthClient:
    """
    Factory function to create the appropriate auth client based on environment

    Args:
        client_type: Optional specific client class to instantiate

    Returns:
        An instance of the appropriate BaseAuthClient implementation
    """
    # If client_type is specified, use it directly
    if client_type:
        return client_type()

    # Otherwise, determine from environment
    environment = os.environ.get("ENVIRONMENT", "local").lower()

    if environment == "gumloop":
        from .clients.GumloopAuthClient import GumloopAuthClient

        return GumloopAuthClient(api_key=api_key)

    # Default to local file auth client
    from .clients.LocalAuthClient import LocalAuthClient

    return LocalAuthClient()
