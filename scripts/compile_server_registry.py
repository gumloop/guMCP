import os
import json
import yaml
import logging
import sys
import argparse
from pathlib import Path
from typing import Dict, Optional, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Required fields in config.yaml
REQUIRED_FIELDS = ["name", "icon", "description", "documentation_path"]


def validate_config(config: Dict[str, Any], server_path: str) -> bool:
    """Validate that the config has all required fields."""
    missing_fields = [field for field in REQUIRED_FIELDS if field not in config]
    if missing_fields:
        logger.warning(
            f"Server {server_path} is missing required fields: {', '.join(missing_fields)}"
        )
        return False
    return True


def read_config_yaml(server_path: str) -> Optional[Dict[str, Any]]:
    """Read and parse the config.yaml file for a server."""
    try:
        config_path = os.path.join(server_path, "config.yaml")
        if not os.path.exists(config_path):
            logger.warning(f"No config.yaml found in {server_path}")
            return None

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        if not validate_config(config, server_path):
            return None

        server_id = os.path.basename(server_path)
        config["server_id"] = server_id

        doc_path = config["documentation_path"]

        config["documentation"] = f"{server_id}/{doc_path}"
        del config["documentation_path"]

        # Add empty tools array if not present
        if "tools" not in config:
            config["tools"] = []

        # Read README content if it exists
        readme_path = os.path.join(server_path, doc_path)
        if os.path.exists(readme_path):
            with open(readme_path, "r") as f:
                config["readme_content"] = f.read()
        else:
            logger.warning(f"No README found at {readme_path}")
            return None  # Skip servers without README

        return config
    except Exception as e:
        logger.error(f"Error processing {server_path}: {str(e)}")
        return None


def generate_server_list(output_path: str) -> bool:
    """Generate a JSON file containing all server configurations.
    Args:
        output_path: Path where the server list JSON should be saved
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        root_dir = Path(__file__).parent.parent
        servers_dir = root_dir / "src" / "servers"

        if not servers_dir.exists():
            logger.error(f"Servers directory not found at {servers_dir}")
            return False

        servers = {}

        # Scan all directories in the servers folder
        for item in os.listdir(servers_dir):
            # Skip simple-tools-server
            if item == "simple-tools-server":
                logger.info(f"Skipping simple-tools-server as requested")
                continue

            item_path = os.path.join(servers_dir, item)
            if os.path.isdir(item_path) and not item.startswith("__"):
                logger.info(f"Processing server: {item}")
                config = read_config_yaml(item_path)
                if config:
                    servers[item] = config

        if not servers:
            logger.error("No valid server configurations found")
            return False

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(servers, f, indent=2)

        logger.info(f"Successfully generated server list at: {output_file}")
        logger.info(f"Total valid servers included: {len(servers)}")
        return True

    except Exception as e:
        logger.error(f"Failed to generate server list: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate a JSON file containing server configurations"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="src/static/server_list.json",
        help="Path where the server list JSON should be saved (default: src/static/server_list.json)",
    )

    args = parser.parse_args()
    success = generate_server_list(args.output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
