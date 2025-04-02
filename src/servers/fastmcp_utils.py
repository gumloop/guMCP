import logging
import importlib.util
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from mcp.server.fastmcp import FastMCP

# Setup logging
logger = logging.getLogger("gumcp-fastmcp")


def extract_capabilities(app: "FastMCP") -> Dict[str, Dict[str, bool]]:
    """Extract the capabilities of a FastMCP instance.

    Args:
        app: FastMCP instance
    Returns:
        Dictionary of capability support status
    """
    return {
        "resources": {"supported": hasattr(app, "resource")},
        "tools": {"supported": hasattr(app, "tool")},
        "prompts": {"supported": hasattr(app, "prompt")},
        "logging": {"supported": True},
        "notifications": {"supported": True},
    }


def create_init_options(app: "FastMCP") -> Dict[str, Any]:
    """Create initialization options for a FastMCP server.

    Args:
        app: FastMCP instance
    Returns:
        Dictionary with server metadata
    """
    return {
        "server_name": app.name,
        "server_version": getattr(app, "version", "1.0.0"),
        "capabilities": extract_capabilities(app),
    }


def create_server_factory(app: "FastMCP") -> Callable:
    """Create a server factory function.

    Args:
        app: FastMCP instance
    Returns:
        Factory function for the server
    """

    def factory(user_id=None, api_key=None):
        return app

    return factory


def create_init_options_factory(app: "FastMCP") -> Callable:
    """Create an initialization options factory function.

    Args:
        app: FastMCP instance
    Returns:
        Factory function for init options
    """

    def get_init_options(server=None):
        return create_init_options(app)

    return get_init_options


def load_fastmcp_server(
    server_path: Path, server_name: str
) -> Tuple[Optional[Callable], Optional[Callable]]:
    """Load a FastMCP server from the specified path.

    Args:
        server_path: Path to the server module file
        server_name: Name of the server
    Returns:
        Tuple of (server_factory, init_options_factory) or (None, None)
    """
    try:
        spec = importlib.util.spec_from_file_location(
            f"{server_name}.server", server_path
        )
        if not spec or not spec.loader:
            return None, None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find FastMCP instance
        fastmcp_instance = None
        for name, obj in module.__dict__.items():
            if isinstance(obj, FastMCP):
                fastmcp_instance = obj
                break

        if fastmcp_instance:
            logger.info(f"Loading FastMCP server: {server_name}")
            return create_server_factory(fastmcp_instance), create_init_options_factory(
                fastmcp_instance
            )
    except Exception as e:
        logger.error(f"Failed to load FastMCP server {server_name}: {e}")

    return None, None
