import os
import sys
import logging
from pathlib import Path


# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)
from src.auth.factory import create_auth_client


def authenticate_and_save_snowflake_credentials(user_id):
    logger.info("Starting Snowflake authentication for user %s...", user_id)
    auth_client = create_auth_client()

    username = input("Enter Snowflake username: ").strip()
    password = input("Enter Snowflake password: ").strip()
    account = input(
        "Enter Snowflake account identifier (e.g., abcd.us-east-1): "
    ).strip()
    database = input("Enter default database: ").strip()
    warehouse = input("Enter default warehouse: ").strip()

    if not all([username, password, account, database, warehouse]):
        raise ValueError("Username, password, and account are required")

    credentials = {
        "username": username,
        "password": password,
        "account": account,
        "database": database,
        "warehouse": warehouse,
    }

    auth_client.save_user_credentials(SERVICE_NAME, user_id, credentials)
    logger.info("Snowflake credentials saved for user %s", user_id)


def get_snowflake_credentials(user_id, api_key=None):
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials(SERVICE_NAME, user_id)

    if not credentials_data:
        raise ValueError(
            f"Snowflake credentials not found for user {user_id}. Run 'auth' first."
        )

    return credentials_data
