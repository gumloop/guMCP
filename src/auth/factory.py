import os
import logging
from typing import Optional, TypeVar, Type

from auth.clients.BaseAuthClient import BaseAuthClient

logger = logging.getLogger("auth-factory")

T = TypeVar('T', bound=BaseAuthClient)

def create_auth_client(client_type: Optional[Type[T]] = None) -> BaseAuthClient:
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
        try:
            from auth.clients.GumloopAuthClient import GumloopAuthClient
            return GumloopAuthClient()
        except ImportError as e:
            logger.warning(f"Gumloop auth client requested but dependencies not available: {str(e)}. "
                          "Falling back to local auth client.")
    
    # Default to local file auth client
    from auth.clients.LocalAuthClient import LocalAuthClient
    return LocalAuthClient() 
