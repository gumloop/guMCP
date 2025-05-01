import os
import sys
import logging
import json
import requests
from pathlib import Path
from typing import Optional, List, Dict, TypedDict, Any, Iterable
from pydantic import AnyUrl

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import TextContent, Resource
from mcp.server.lowlevel.helper_types import ReadResourceContents

from src.utils.pipedrive.util import (
    authenticate_and_save_credentials,
    get_credentials,
)

SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(SERVICE_NAME)


# Type definitions for Pipedrive entities
class Deal(TypedDict):
    id: int
    title: str
    value: float
    currency: str
    status: str
    owner_id: int
    org_id: int
    person_id: int


class Person(TypedDict):
    id: int
    name: str
    email: List[Dict[str, str]]
    phone: List[Dict[str, str]]
    org_id: int


class Organization(TypedDict):
    id: int
    name: str
    address: str


class PipedriveClient:
    """Client for interacting with the Pipedrive API."""

    def __init__(self, access_token: str, api_domain: str = None):
        """Initialize the Pipedrive client with an access token."""
        self.access_token = access_token
        self.base_url = api_domain or "https://api.pipedrive.com/v1"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self, method: str, endpoint: str, params: Dict = None, data: Dict = None
    ) -> Dict:
        """Make a request to the Pipedrive API."""
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(
            method=method, url=url, headers=self.headers, params=params, json=data
        )
        if response.status_code in [200, 201]:
            return response.json()
        elif response.status_code in [204, 410]:
            return {"status": "success", "data": response.json().get("data", {})}
        else:
            logger.error(f"Error: {response.status_code} - {response.text}")
            raise Exception(f"Error: {response.status_code} - {response.text}")

    # Activity Operations
    def create_activity(
        self,
        subject: str,
        type: str,
        due_date: str,
        due_time: Optional[str] = None,
        duration: Optional[str] = None,
        user_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        person_id: Optional[int] = None,
        org_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> Dict:
        """Create a new activity in Pipedrive."""
        data = {
            "subject": subject,
            "type": type,
            "due_date": due_date,
        }
        if due_time:
            data["due_time"] = due_time
        if duration:
            data["duration"] = duration
        if user_id:
            data["user_id"] = user_id
        if deal_id:
            data["deal_id"] = deal_id
        if person_id:
            data["person_id"] = person_id
        if org_id:
            data["org_id"] = org_id
        if note:
            data["note"] = note

        return self._make_request("POST", "activities", data=data)

    def get_activity(self, activity_id: int) -> Dict:
        """Get a specific activity from Pipedrive."""
        return self._make_request("GET", f"activities/{activity_id}")

    def update_activity(
        self,
        activity_id: int,
        subject: Optional[str] = None,
        type: Optional[str] = None,
        due_date: Optional[str] = None,
        due_time: Optional[str] = None,
        duration: Optional[str] = None,
        user_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        person_id: Optional[int] = None,
        org_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> Dict:
        """Update an activity in Pipedrive."""
        data = {}
        if subject:
            data["subject"] = subject
        if type:
            data["type"] = type
        if due_date:
            data["due_date"] = due_date
        if due_time:
            data["due_time"] = due_time
        if duration:
            data["duration"] = duration
        if user_id:
            data["user_id"] = user_id
        if deal_id:
            data["deal_id"] = deal_id
        if person_id:
            data["person_id"] = person_id
        if org_id:
            data["org_id"] = org_id
        if note:
            data["note"] = note

        return self._make_request("PUT", f"activities/{activity_id}", data=data)

    def delete_activity(self, activity_id: int) -> Dict:
        """Delete an activity from Pipedrive."""
        return self._make_request("DELETE", f"activities/{activity_id}")

    # Deal Operations
    def create_deal(
        self,
        title: str,
        org_id: Optional[int] = None,
        value: Optional[float] = None,
        currency: Optional[str] = None,
        user_id: Optional[int] = None,
        person_id: Optional[int] = None,
        stage_id: Optional[int] = None,
        status: Optional[str] = None,
        probability: Optional[int] = None,
        expected_close_date: Optional[str] = None,
        visible_to: Optional[int] = None,
        add_time: Optional[str] = None,
        custom_fields: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a new deal in Pipedrive.

        Args:
            title (str): The title of the deal (required)
            org_id (int, optional): The ID of the organization this deal will be associated with
            value (float, optional): The value of the deal
            currency (str, optional): The currency of the deal
            user_id (int, optional): The ID of the user who will be marked as the owner of this deal
            person_id (int, optional): The ID of the person this deal will be associated with
            stage_id (int, optional): The ID of the stage this deal will be placed in a pipeline
            status (str, optional): The status of the deal (open, won, lost, deleted)
            probability (int, optional): The success probability percentage of the deal
            expected_close_date (str, optional): The expected close date of the deal (YYYY-MM-DD)
            visible_to (int, optional): The visibility of the deal (1 = owner & followers, 3 = entire company)
            add_time (str, optional): The creation date & time of the deal (YYYY-MM-DD HH:MM:SS)
            custom_fields (Dict, optional): Custom fields to add to the deal

        Returns:
            Dict: The created deal data

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not title:
            raise ValueError("Title is required to create a deal")

        data = {"title": title}

        # Add optional parameters if provided
        if org_id is not None:
            data["org_id"] = org_id
        if value is not None:
            data["value"] = value
        if currency is not None:
            data["currency"] = currency
        if user_id is not None:
            data["user_id"] = user_id
        if person_id is not None:
            data["person_id"] = person_id
        if stage_id is not None:
            data["stage_id"] = stage_id
        if status is not None:
            if status not in ["open", "won", "lost", "deleted"]:
                raise ValueError("Status must be one of: open, won, lost, deleted")
            data["status"] = status
        if probability is not None:
            if not 0 <= probability <= 100:
                raise ValueError("Probability must be between 0 and 100")
            data["probability"] = probability
        if expected_close_date is not None:
            data["expected_close_date"] = expected_close_date
        if visible_to is not None:
            if visible_to not in [1, 3]:
                raise ValueError(
                    "Visible_to must be either 1 (owner & followers) or 3 (entire company)"
                )
            data["visible_to"] = visible_to
        if add_time is not None:
            data["add_time"] = add_time
        if custom_fields is not None:
            data.update(custom_fields)

        return self._make_request("POST", "deals", data=data)

    def get_deal(self, deal_id: int) -> Dict:
        """Get a specific deal from Pipedrive."""
        return self._make_request("GET", f"deals/{deal_id}")

    def update_deal(
        self,
        deal_id: int,
        title: Optional[str] = None,
        value: Optional[float] = None,
        currency: Optional[str] = None,
        status: Optional[str] = None,
        owner_id: Optional[int] = None,
        org_id: Optional[int] = None,
        person_id: Optional[int] = None,
        custom_fields: Optional[Dict] = None,
    ) -> Dict:
        """Update a deal in Pipedrive."""
        data = {}
        if title:
            data["title"] = title
        if value:
            data["value"] = value
        if currency:
            data["currency"] = currency
        if status:
            data["status"] = status
        if owner_id:
            data["owner_id"] = owner_id
        if org_id:
            data["org_id"] = org_id
        if person_id:
            data["person_id"] = person_id
        if custom_fields:
            data.update(custom_fields)

        return self._make_request("PUT", f"deals/{deal_id}", data=data)

    def delete_deal(self, deal_id: int) -> Dict:
        """Delete a deal from Pipedrive."""
        return self._make_request("DELETE", f"deals/{deal_id}")

    # Lead Operations
    def create_lead(
        self,
        title: str,
        person_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        value: Optional[Dict[str, Any]] = None,
        owner_id: Optional[int] = None,
        label_ids: Optional[List[str]] = None,
        expected_close_date: Optional[str] = None,
        visible_to: Optional[int] = None,
        was_seen: Optional[bool] = None,
        custom_fields: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a new lead in Pipedrive.

        Args:
            title (str): The title of the lead (required)
            person_id (int, optional): The ID of the person this lead will be associated with
            organization_id (int, optional): The ID of the organization this lead will be associated with
            value (Dict[str, Any], optional): The value of the lead in format {"amount": float, "currency": str}
            owner_id (int, optional): The ID of the user who will be marked as the owner of this lead
            label_ids (List[str], optional): The IDs of the labels associated with this lead
            expected_close_date (str, optional): The expected close date of the lead (YYYY-MM-DD)
            visible_to (int, optional): The visibility of the lead (1 = owner & followers, 3 = entire company)
            was_seen (bool, optional): Whether the lead was seen by someone in the Pipedrive account
            custom_fields (Dict, optional): Custom fields to add to the lead

        Returns:
            Dict: The created lead data

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not title:
            raise ValueError("Title is required to create a lead")

        if not person_id and not organization_id:
            raise ValueError("Either person_id or organization_id must be provided")

        data = {"title": title}

        # Add required parameters
        if person_id is not None:
            data["person_id"] = person_id
        if organization_id is not None:
            data["organization_id"] = organization_id

        # Add optional parameters if provided
        if value is not None:
            if (
                not isinstance(value, dict)
                or "amount" not in value
                or "currency" not in value
            ):
                raise ValueError(
                    "Value must be a dictionary with 'amount' and 'currency' keys"
                )
            data["value"] = value
        if owner_id is not None:
            data["owner_id"] = owner_id
        if label_ids is not None:
            data["label_ids"] = label_ids
        if expected_close_date is not None:
            data["expected_close_date"] = expected_close_date
        if visible_to is not None:
            if visible_to not in [1, 3]:
                raise ValueError(
                    "Visible_to must be either 1 (owner & followers) or 3 (entire company)"
                )
            data["visible_to"] = visible_to
        if was_seen is not None:
            data["was_seen"] = was_seen
        if custom_fields is not None:
            data.update(custom_fields)

        return self._make_request("POST", "leads", data=data)

    def get_lead(self, lead_id: str) -> Dict:
        """Get a specific lead from Pipedrive."""
        return self._make_request("GET", f"leads/{lead_id}")

    def delete_lead(self, lead_id: str) -> Dict:
        """Delete a lead from Pipedrive."""
        return self._make_request("DELETE", f"leads/{lead_id}")

    # Note Operations
    def create_note(
        self,
        content: str,
        person_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        user_id: Optional[int] = None,
        pinned_to_deal_flag: Optional[bool] = None,
        pinned_to_organization_flag: Optional[bool] = None,
        pinned_to_person_flag: Optional[bool] = None,
    ) -> Dict:
        """
        Create a new note in Pipedrive.

        Args:
            content (str): The content of the note (required)
            person_id (int, optional): The ID of the person this note will be associated with
            organization_id (int, optional): The ID of the organization this note will be associated with
            deal_id (int, optional): The ID of the deal this note will be associated with
            user_id (int, optional): The ID of the user who will be marked as the author of this note
            pinned_to_deal_flag (bool, optional): Whether the note is pinned to the deal
            pinned_to_organization_flag (bool, optional): Whether the note is pinned to the organization
            pinned_to_person_flag (bool, optional): Whether the note is pinned to the person

        Returns:
            Dict: The created note data

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not content:
            raise ValueError("Content is required to create a note")

        if not person_id and not organization_id and not deal_id:
            raise ValueError(
                "At least one of person_id, organization_id, or deal_id must be provided"
            )

        data = {"content": content}

        # Add required parameters
        if person_id is not None:
            data["person_id"] = person_id
        if organization_id is not None:
            data["org_id"] = organization_id
        if deal_id is not None:
            data["deal_id"] = deal_id

        # Add optional parameters if provided
        if user_id is not None:
            data["user_id"] = user_id
        if pinned_to_deal_flag is not None:
            data["pinned_to_deal_flag"] = pinned_to_deal_flag
        if pinned_to_organization_flag is not None:
            data["pinned_to_organization_flag"] = pinned_to_organization_flag
        if pinned_to_person_flag is not None:
            data["pinned_to_person_flag"] = pinned_to_person_flag

        return self._make_request("POST", "notes", data=data)

    def get_note(self, note_id: int) -> Dict:
        """Get a specific note from Pipedrive."""
        return self._make_request("GET", f"notes/{note_id}")

    def update_note(
        self,
        note_id: int,
        content: Optional[str] = None,
        deal_id: Optional[int] = None,
        person_id: Optional[int] = None,
        org_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict:
        """Update a note in Pipedrive."""
        data = {}
        if content:
            data["content"] = content
        if deal_id:
            data["deal_id"] = deal_id
        if person_id:
            data["person_id"] = person_id
        if org_id:
            data["org_id"] = org_id
        if user_id:
            data["user_id"] = user_id

        return self._make_request("PUT", f"notes/{note_id}", data=data)

    def delete_note(self, note_id: int) -> Dict:
        """Delete a note from Pipedrive."""
        return self._make_request("DELETE", f"notes/{note_id}")

    # Person Operations
    def create_person(
        self,
        name: str,
        email: Optional[List[Dict[str, str]]] = None,
        phone: Optional[List[Dict[str, str]]] = None,
        org_id: Optional[int] = None,
        custom_fields: Optional[Dict] = None,
    ) -> Dict:
        """Create a new person in Pipedrive."""
        data = {"name": name}
        if email:
            data["email"] = email
        if phone:
            data["phone"] = phone
        if org_id:
            data["org_id"] = org_id
        if custom_fields:
            data.update(custom_fields)

        return self._make_request("POST", "persons", data=data)

    def get_person(self, person_id: int) -> Dict:
        """Get a specific person from Pipedrive."""
        return self._make_request("GET", f"persons/{person_id}")

    def update_person(
        self,
        person_id: int,
        name: Optional[str] = None,
        email: Optional[List[Dict[str, str]]] = None,
        phone: Optional[List[Dict[str, str]]] = None,
        org_id: Optional[int] = None,
        custom_fields: Optional[Dict] = None,
    ) -> Dict:
        """Update a person in Pipedrive."""
        data = {}
        if name:
            data["name"] = name
        if email:
            data["email"] = email
        if phone:
            data["phone"] = phone
        if org_id:
            data["org_id"] = org_id
        if custom_fields:
            data.update(custom_fields)

        return self._make_request("PUT", f"persons/{person_id}", data=data)

    def delete_person(self, person_id: int) -> Dict:
        """Delete a person from Pipedrive.

        Note: This is a soft delete operation. The person will be marked as inactive
        but will still exist in the system with active_flag set to false.
        """
        return self._make_request("DELETE", f"persons/{person_id}")

    # Product Operations
    def create_product(
        self,
        name: str,
        code: str,
        unit: str,
        prices: List[Dict[str, float]],
        active_flag: bool = True,
        visible_to: int = 3,
        owner_id: Optional[int] = None,
    ) -> Dict:
        """Create a new product in Pipedrive."""
        data = {
            "name": name,
            "code": code,
            "unit": unit,
            "prices": prices,
            "active_flag": active_flag,
            "visible_to": visible_to,
        }
        if owner_id:
            data["owner_id"] = owner_id

        return self._make_request("POST", "products", data=data)

    def get_product(self, product_id: int) -> Dict:
        """Get a specific product from Pipedrive."""
        return self._make_request("GET", f"products/{product_id}")

    def update_product(
        self,
        product_id: int,
        name: Optional[str] = None,
        code: Optional[str] = None,
        unit: Optional[str] = None,
        prices: Optional[List[Dict[str, float]]] = None,
        active_flag: Optional[bool] = None,
        visible_to: Optional[int] = None,
        owner_id: Optional[int] = None,
    ) -> Dict:
        """Update a product in Pipedrive."""
        data = {}
        if name:
            data["name"] = name
        if code:
            data["code"] = code
        if unit:
            data["unit"] = unit
        if prices:
            data["prices"] = prices
        if active_flag is not None:
            data["active_flag"] = active_flag
        if visible_to:
            data["visible_to"] = visible_to
        if owner_id:
            data["owner_id"] = owner_id

        return self._make_request("PUT", f"products/{product_id}", data=data)

    def delete_product(self, product_id: int) -> Dict:
        """Delete a product from Pipedrive."""
        return self._make_request("DELETE", f"products/{product_id}")

    # Organization Operations
    def create_organization(
        self,
        name: str,
        address: Optional[str] = None,
        visible_to: Optional[int] = None,
        custom_fields: Optional[Dict] = None,
    ) -> Dict:
        """Create a new organization in Pipedrive."""
        data = {"name": name}
        if address:
            data["address"] = address
        if visible_to:
            data["visible_to"] = visible_to
        if custom_fields:
            data.update(custom_fields)

        return self._make_request("POST", "organizations", data=data)

    def get_organization(self, org_id: int) -> Dict:
        """Get a specific organization from Pipedrive."""
        return self._make_request("GET", f"organizations/{org_id}")

    def update_organization(
        self,
        org_id: int,
        name: Optional[str] = None,
        address: Optional[str] = None,
        visible_to: Optional[int] = None,
        custom_fields: Optional[Dict] = None,
    ) -> Dict:
        """Update an organization in Pipedrive."""
        data = {}
        if name:
            data["name"] = name
        if address:
            data["address"] = address
        if visible_to:
            data["visible_to"] = visible_to
        if custom_fields:
            data.update(custom_fields)

        return self._make_request("PUT", f"organizations/{org_id}", data=data)

    def delete_organization(self, org_id: int) -> Dict:
        """Delete an organization from Pipedrive."""
        return self._make_request("DELETE", f"organizations/{org_id}")

    # User Operations
    def get_all_users(self) -> Dict:
        """Get all users from Pipedrive."""
        return self._make_request("GET", "users")

    # Get All Operations
    def get_all_leads(
        self,
        start: int = 0,
        limit: int = 100,
        sort: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict:
        """Get all leads from Pipedrive."""
        params = {
            "start": start,
            "limit": limit,
        }
        if sort:
            params["sort"] = sort
        if status:
            params["status"] = status

        return self._make_request("GET", "leads", params=params)

    def get_all_products(
        self,
        start: int = 0,
        limit: int = 100,
        sort: Optional[str] = None,
    ) -> Dict:
        """Get all products from Pipedrive."""
        params = {
            "start": start,
            "limit": limit,
        }
        if sort:
            params["sort"] = sort

        return self._make_request("GET", "products", params=params)

    def get_all_persons(
        self,
        start: int = 0,
        limit: int = 100,
        sort: Optional[str] = None,
    ) -> Dict:
        """Get all persons from Pipedrive."""
        params = {
            "start": start,
            "limit": limit,
        }
        if sort:
            params["sort"] = sort

        return self._make_request("GET", "persons", params=params)

    def get_all_organizations(
        self,
        start: int = 0,
        limit: int = 100,
        sort: Optional[str] = None,
    ) -> Dict:
        """Get all organizations from Pipedrive."""
        params = {
            "start": start,
            "limit": limit,
        }
        if sort:
            params["sort"] = sort

        return self._make_request("GET", "organizations", params=params)


async def create_pipedrive_client(user_id: str, api_key: str) -> PipedriveClient:
    """
    Create an authorized Pipedrive API client.

    Args:
        user_id (str): The user ID associated with the credentials

    Returns:
        PipedriveClient: Pipedrive API client with credentials initialized
    """
    credentials = await get_credentials(user_id, SERVICE_NAME, api_key)
    if not credentials or not isinstance(credentials, dict):
        raise ValueError("Invalid credentials format")

    # Extract API token and domain from the credentials
    api_token = credentials.get("access_token")
    api_domain = credentials.get("api_domain")

    if not api_token:
        raise ValueError("No access token found in credentials")

    return PipedriveClient(api_token, api_domain)


def create_server(user_id: str, api_key: str = None) -> Server:
    """
    Initialize and configure the Pipedrive MCP server.

    Args:
        user_id (str): The user ID associated with the current session
        api_key (str, optional): Optional API key override

    Returns:
        Server: Configured MCP server instance
    """
    server = Server("pipedrive-server")

    server.user_id = user_id
    server.api_key = api_key
    server._pipedrive_client = None

    async def _get_pipedrive_client() -> PipedriveClient:
        """Get or create a Pipedrive client."""
        if not server._pipedrive_client:
            server._pipedrive_client = await create_pipedrive_client(
                server.user_id, server.api_key
            )
        return server._pipedrive_client

    @server.list_resources()
    async def handle_list_resources() -> list[Resource]:
        """List available Pipedrive resources."""
        logger.info(f"Listing resources for user: {server.user_id}")

        try:
            client = await _get_pipedrive_client()
            resources = []

            # List all persons
            persons_response = client.get_all_persons()
            persons_data = persons_response.get("data")
            if persons_data is None:
                persons_data = []
            for person in persons_data:
                person_id = person.get("id")
                person_name = person.get("name", "Unknown Person")
                resources.append(
                    Resource(
                        uri=f"pipedrive://person/{person_id}",
                        mimeType="application/json",
                        name=f"Person: {person_name}",
                        description=f"Pipedrive contact: {person_name}",
                    )
                )

            # List all organizations
            orgs_response = client.get_all_organizations()
            orgs_data = orgs_response.get("data")
            if orgs_data is None:
                orgs_data = []
            for org in orgs_data:
                org_id = org.get("id")
                org_name = org.get("name", "Unknown Organization")
                resources.append(
                    Resource(
                        uri=f"pipedrive://organization/{org_id}",
                        mimeType="application/json",
                        name=f"Organization: {org_name}",
                        description=f"Pipedrive organization: {org_name}",
                    )
                )
            # List all deals
            deals_response = client._make_request("GET", "deals")
            deals_data = deals_response.get("data")
            if deals_data is None:
                deals_data = []
            for deal in deals_data:
                deal_id = deal.get("id")
                deal_title = deal.get("title", "Unknown Deal")
                deal_status = deal.get("status", "unknown")
                deal_value = deal.get("value", 0)
                deal_currency = deal.get("currency", "")

                resources.append(
                    Resource(
                        uri=f"pipedrive://deal/{deal_id}",
                        mimeType="application/json",
                        name=f"Deal: {deal_title}",
                        description=f"Pipedrive deal: {deal_title} ({deal_status}) - {deal_value} {deal_currency}",
                    )
                )

            # List all leads
            leads_response = client.get_all_leads()
            leads_data = leads_response.get("data")
            if leads_data is None:
                leads_data = []
            for lead in leads_data:
                lead_id = lead.get("id")
                lead_title = lead.get("title", "Unknown Lead")

                resources.append(
                    Resource(
                        uri=f"pipedrive://lead/{lead_id}",
                        mimeType="application/json",
                        name=f"Lead: {lead_title}",
                        description=f"Pipedrive lead: {lead_title}",
                    )
                )

            # List all products
            products_response = client.get_all_products()
            products_data = products_response.get("data")
            if products_data is None:
                products_data = []
            for product in products_data:
                product_id = product.get("id")
                product_name = product.get("name", "Unknown Product")
                product_code = product.get("code", "")

                resources.append(
                    Resource(
                        uri=f"pipedrive://product/{product_id}",
                        mimeType="application/json",
                        name=f"Product: {product_name}",
                        description=f"Pipedrive product: {product_name} (Code: {product_code})",
                    )
                )

            return resources

        except Exception as e:
            logger.error(
                f"Error listing Pipedrive resources: {str(e)} {e.__traceback__.tb_lineno}"
            )
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a Pipedrive resource by URI."""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        try:
            client = await _get_pipedrive_client()
            uri_str = str(uri)

            if not uri_str.startswith("pipedrive://"):
                raise ValueError(f"Invalid Pipedrive URI: {uri_str}")

            # Parse the URI to get resource type and ID
            parts = uri_str.replace("pipedrive://", "").split("/")
            if len(parts) != 2:
                raise ValueError(f"Invalid Pipedrive URI format: {uri_str}")

            resource_type, resource_id = parts

            # Get the resource data based on type
            if resource_type == "person":
                data = client.get_person(int(resource_id))
            elif resource_type == "organization":
                data = client.get_organization(int(resource_id))
            elif resource_type == "deal":
                data = client._make_request("GET", f"deals/{resource_id}")
            elif resource_type == "lead":
                data = client._make_request("GET", f"leads/{resource_id}")
            elif resource_type == "product":
                data = client.get_product(int(resource_id))
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")

            formatted_content = json.dumps(data, indent=2)
            return [
                ReadResourceContents(
                    content=formatted_content, mime_type="application/json"
                )
            ]

        except Exception as e:
            logger.error(f"Error reading Pipedrive resource: {str(e)}")
            raise ValueError(f"Error reading resource: {str(e)}")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Return a list of available Pipedrive tools.

        Returns:
            list[types.Tool]: List of tool definitions supported by this server
        """
        return [
            # Activity Operations
            types.Tool(
                name="create_activity",
                description="Create a new activity in Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": [
                                "call",
                                "meeting",
                                "task",
                                "deadline",
                                "email",
                                "lunch",
                                "note",
                            ],
                        },
                        "due_date": {"type": "string", "format": "date"},
                        "due_time": {"type": "string", "format": "time"},
                        "duration": {"type": "string"},
                        "user_id": {"type": "integer"},
                        "deal_id": {"type": "integer"},
                        "person_id": {"type": "integer"},
                        "org_id": {"type": "integer"},
                        "note": {"type": "string"},
                    },
                    "required": ["subject", "type", "due_date"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the created activity data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "subject": "Meeting with client", '
                        '"type": "meeting", "due_date": "2024-03-20", "due_time": "14:00", '
                        '"duration": "1h", "user_id": 123, "deal_id": 456, "person_id": 789, '
                        '"org_id": 101, "note": "Discuss project requirements"}}'
                    ],
                },
            ),
            types.Tool(
                name="get_activity",
                description="Get a specific activity from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"activity_id": {"type": "integer"}},
                    "required": ["activity_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the activity data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "subject": "Meeting with client", '
                        '"type": "meeting", "due_date": "2024-03-20", "due_time": "14:00", '
                        '"duration": "1h", "user_id": 123, "deal_id": 456, "person_id": 789, '
                        '"org_id": 101, "note": "Discuss project requirements"}}'
                    ],
                },
            ),
            types.Tool(
                name="update_activity",
                description="Update an activity in Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "activity_id": {"type": "integer"},
                        "subject": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": [
                                "call",
                                "meeting",
                                "task",
                                "deadline",
                                "email",
                                "lunch",
                                "note",
                            ],
                        },
                        "due_date": {"type": "string", "format": "date"},
                        "due_time": {"type": "string", "format": "time"},
                        "duration": {"type": "string"},
                        "user_id": {"type": "integer"},
                        "deal_id": {"type": "integer"},
                        "person_id": {"type": "integer"},
                        "org_id": {"type": "integer"},
                        "note": {"type": "string"},
                    },
                    "required": ["activity_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the updated activity data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "subject": "Updated Meeting", '
                        '"type": "meeting", "due_date": "2024-03-21", "due_time": "15:00", '
                        '"duration": "2h", "user_id": 123, "deal_id": 456, "person_id": 789, '
                        '"org_id": 101, "note": "Updated discussion points"}}'
                    ],
                },
            ),
            types.Tool(
                name="delete_activity",
                description="Delete an activity from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"activity_id": {"type": "integer"}},
                    "required": ["activity_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the deletion result",
                    "examples": ['{"success": true, "data": {"id": 1}}'],
                },
            ),
            # Deal Operations
            types.Tool(
                name="create_deal",
                description="Create a new deal in Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "org_id": {"type": "integer"},
                        "value": {"type": "number"},
                        "currency": {"type": "string"},
                        "user_id": {"type": "integer"},
                        "person_id": {"type": "integer"},
                        "stage_id": {"type": "integer"},
                        "status": {
                            "type": "string",
                            "enum": ["open", "won", "lost", "deleted"],
                        },
                        "probability": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "expected_close_date": {"type": "string", "format": "date"},
                        "visible_to": {"type": "integer", "enum": [1, 3]},
                        "add_time": {"type": "string", "format": "date-time"},
                    },
                    "required": ["title"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the created deal data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "title": "New Deal", '
                        '"org_id": 123, "value": 1000, "currency": "USD", "user_id": 456, '
                        '"person_id": 789, "stage_id": 101, "status": "open", '
                        '"probability": 50, "expected_close_date": "2024-12-31", '
                        '"visible_to": 3, "add_time": "2024-03-20 10:00:00"}}'
                    ],
                },
            ),
            types.Tool(
                name="get_deal",
                description="Get a specific deal from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"deal_id": {"type": "integer"}},
                    "required": ["deal_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the deal data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "title": "Existing Deal", '
                        '"org_id": 123, "value": 1000, "currency": "USD", "user_id": 456, '
                        '"person_id": 789, "stage_id": 101, "status": "open", '
                        '"probability": 50, "expected_close_date": "2024-12-31", '
                        '"visible_to": 3, "add_time": "2024-03-20 10:00:00"}}'
                    ],
                },
            ),
            types.Tool(
                name="update_deal",
                description="Update a deal in Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "deal_id": {"type": "integer"},
                        "title": {"type": "string"},
                        "value": {"type": "number"},
                        "currency": {"type": "string"},
                        "user_id": {"type": "integer"},
                        "person_id": {"type": "integer"},
                        "org_id": {"type": "integer"},
                        "stage_id": {"type": "integer"},
                        "status": {
                            "type": "string",
                            "enum": ["open", "won", "lost", "deleted"],
                        },
                        "probability": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "expected_close_date": {"type": "string", "format": "date"},
                        "visible_to": {"type": "integer", "enum": [1, 3]},
                    },
                    "required": ["deal_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the updated deal data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "title": "Updated Deal", '
                        '"org_id": 123, "value": 1500, "currency": "USD", "user_id": 456, '
                        '"person_id": 789, "stage_id": 101, "status": "open", '
                        '"probability": 75, "expected_close_date": "2024-12-31", '
                        '"visible_to": 3, "add_time": "2024-03-20 10:00:00"}}'
                    ],
                },
            ),
            types.Tool(
                name="delete_deal",
                description="Delete a deal from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"deal_id": {"type": "integer"}},
                    "required": ["deal_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the deletion result",
                    "examples": ['{"success": true, "data": {"id": 1}}'],
                },
            ),
            # Lead Operations
            types.Tool(
                name="create_lead",
                description="Create a new lead in Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "person_id": {"type": "integer"},
                        "organization_id": {"type": "integer"},
                        "value": {
                            "type": "object",
                            "properties": {
                                "amount": {"type": "number"},
                                "currency": {"type": "string"},
                            },
                        },
                        "owner_id": {"type": "integer"},
                        "label_ids": {"type": "array", "items": {"type": "integer"}},
                        "expected_close_date": {"type": "string", "format": "date"},
                        "visible_to": {"type": "integer", "enum": [1, 3, 5, 7]},
                        "was_seen": {"type": "boolean"},
                        "custom_fields": {"type": "object"},
                    },
                    "required": ["title", "person_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the created lead data",
                    "examples": [
                        '{"success": true, "data": {"id": "52e93d20-2603-11f0-a826-1f8b4459f0ad", '
                        '"title": "New Lead", "person_id": 123, "organization_id": 456, '
                        '"value": {"amount": 1000, "currency": "USD"}, "owner_id": 789, '
                        '"label_ids": [1, 2, 3], "expected_close_date": "2024-12-31", '
                        '"visible_to": 3, "was_seen": false}}'
                    ],
                },
            ),
            types.Tool(
                name="get_lead",
                description="Get a specific lead from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"lead_id": {"type": "string"}},
                    "required": ["lead_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the lead data",
                    "examples": [
                        '{"success": true, "data": {"id": "52e93d20-2603-11f0-a826-1f8b4459f0ad", '
                        '"title": "Existing Lead", "person_id": 123, "organization_id": 456, '
                        '"value": {"amount": 1000, "currency": "USD"}, "owner_id": 789, '
                        '"label_ids": [1, 2, 3], "expected_close_date": "2024-12-31", '
                        '"visible_to": 3, "was_seen": true}}'
                    ],
                },
            ),
            types.Tool(
                name="delete_lead",
                description="Delete a lead from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"lead_id": {"type": "string"}},
                    "required": ["lead_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the deletion result",
                    "examples": [
                        '{"success": true, "data": {"id": "52e93d20-2603-11f0-a826-1f8b4459f0ad"}}'
                    ],
                },
            ),
            # Note Operations
            types.Tool(
                name="create_note",
                description="Create a new note in Pipedrive. At least one of person_id, organization_id, or deal_id must be provided.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "person_id": {"type": "integer"},
                        "organization_id": {"type": "integer"},
                        "deal_id": {"type": "integer"},
                        "user_id": {"type": "integer"},
                        "pinned_to_deal_flag": {"type": "boolean"},
                        "pinned_to_organization_flag": {"type": "boolean"},
                        "pinned_to_person_flag": {"type": "boolean"},
                    },
                    "required": ["content"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the created note data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "content": "Meeting notes", '
                        '"person_id": 123, "organization_id": 456, "deal_id": 789, '
                        '"user_id": 101, "pinned_to_deal_flag": true, '
                        '"pinned_to_organization_flag": false, "pinned_to_person_flag": true}}'
                    ],
                },
            ),
            types.Tool(
                name="get_note",
                description="Get a specific note from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"note_id": {"type": "integer"}},
                    "required": ["note_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the note data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "content": "Meeting notes", '
                        '"person_id": 123, "organization_id": 456, "deal_id": 789, '
                        '"user_id": 101, "pinned_to_deal_flag": true, '
                        '"pinned_to_organization_flag": false, "pinned_to_person_flag": true}}'
                    ],
                },
            ),
            types.Tool(
                name="update_note",
                description="Update a note in Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {"type": "integer"},
                        "content": {"type": "string"},
                        "deal_id": {"type": "integer"},
                        "person_id": {"type": "integer"},
                        "org_id": {"type": "integer"},
                        "user_id": {"type": "integer"},
                        "pinned_to_deal_flag": {"type": "boolean"},
                        "pinned_to_organization_flag": {"type": "boolean"},
                        "pinned_to_person_flag": {"type": "boolean"},
                    },
                    "required": ["note_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the updated note data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "content": "Updated meeting notes", '
                        '"person_id": 123, "organization_id": 456, "deal_id": 789, '
                        '"user_id": 101, "pinned_to_deal_flag": true, '
                        '"pinned_to_organization_flag": false, "pinned_to_person_flag": true}}'
                    ],
                },
            ),
            types.Tool(
                name="delete_note",
                description="Delete a note from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"note_id": {"type": "integer"}},
                    "required": ["note_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the deletion result",
                    "examples": ['{"success": true, "data": {"id": 1}}'],
                },
            ),
            # Person Operations
            types.Tool(
                name="create_person",
                description="Create a new person in Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "string"},
                                    "primary": {"type": "boolean"},
                                    "label": {"type": "string"},
                                },
                            },
                        },
                        "phone": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "string"},
                                    "primary": {"type": "boolean"},
                                    "label": {"type": "string"},
                                },
                            },
                        },
                        "org_id": {"type": "integer"},
                        "visible_to": {"type": "integer", "enum": [1, 3, 5, 7]},
                        "add_time": {"type": "string", "format": "date-time"},
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the created person data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "name": "John Doe", '
                        '"email": [{"value": "john@example.com", "primary": true, '
                        '"label": "work"}], "phone": [{"value": "+1234567890", '
                        '"primary": true, "label": "mobile"}], "org_id": 123, '
                        '"visible_to": 3, "add_time": "2024-03-20 10:00:00"}}'
                    ],
                },
            ),
            types.Tool(
                name="get_person",
                description="Get a specific person from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"person_id": {"type": "integer"}},
                    "required": ["person_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the person data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "name": "John Doe", '
                        '"email": [{"value": "john@example.com", "primary": true, '
                        '"label": "work"}], "phone": [{"value": "+1234567890", '
                        '"primary": true, "label": "mobile"}], "org_id": 123, '
                        '"visible_to": 3, "add_time": "2024-03-20 10:00:00"}}'
                    ],
                },
            ),
            types.Tool(
                name="update_person",
                description="Update a person in Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "person_id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "string"},
                                    "primary": {"type": "boolean"},
                                    "label": {"type": "string"},
                                },
                            },
                        },
                        "phone": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "string"},
                                    "primary": {"type": "boolean"},
                                    "label": {"type": "string"},
                                },
                            },
                        },
                        "org_id": {"type": "integer"},
                        "visible_to": {"type": "integer", "enum": [1, 3, 5, 7]},
                    },
                    "required": ["person_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the updated person data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "name": "John Doe", '
                        '"email": [{"value": "john@example.com", "primary": true, '
                        '"label": "work"}], "phone": [{"value": "+1234567890", '
                        '"primary": true, "label": "mobile"}], "org_id": 123, '
                        '"visible_to": 3, "add_time": "2024-03-20 10:00:00"}}'
                    ],
                },
            ),
            types.Tool(
                name="delete_person",
                description="Delete a person from Pipedrive.",
                inputSchema={
                    "type": "object",
                    "properties": {"person_id": {"type": "integer"}},
                    "required": ["person_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the deletion result",
                    "examples": ['{"success": true, "data": {"id": 1}}'],
                },
            ),
            # Product Operations
            types.Tool(
                name="create_product",
                description="Create a new product in Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "code": {"type": "string"},
                        "unit": {"type": "string"},
                        "prices": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "price": {"type": "number"},
                                    "currency": {"type": "string"},
                                },
                            },
                        },
                        "active_flag": {"type": "boolean"},
                        "visible_to": {"type": "integer", "enum": [1, 3, 5, 7]},
                        "owner_id": {"type": "integer"},
                    },
                    "required": ["name", "code", "unit", "prices"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the created product data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "name": "Premium Plan", '
                        '"code": "PRM-001", "unit": "month", "prices": [{"price": 99.99, '
                        '"currency": "USD"}], "active_flag": true, "visible_to": 3, '
                        '"owner_id": 123}}'
                    ],
                },
            ),
            types.Tool(
                name="get_product",
                description="Get a specific product from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"product_id": {"type": "integer"}},
                    "required": ["product_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the product data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "name": "Premium Plan", '
                        '"code": "PRM-001", "unit": "month", "prices": [{"price": 99.99, '
                        '"currency": "USD"}], "active_flag": true, "visible_to": 3, '
                        '"owner_id": 123}}'
                    ],
                },
            ),
            types.Tool(
                name="update_product",
                description="Update a product in Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer"},
                        "name": {"type": "string"},
                        "code": {"type": "string"},
                        "unit": {"type": "string"},
                        "prices": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "price": {"type": "number"},
                                    "currency": {"type": "string"},
                                },
                            },
                        },
                        "active_flag": {"type": "boolean"},
                        "visible_to": {"type": "integer", "enum": [1, 3, 5, 7]},
                        "owner_id": {"type": "integer"},
                    },
                    "required": ["product_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the updated product data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "name": "Updated Premium Plan", '
                        '"code": "PRM-001", "unit": "month", "prices": [{"price": 149.99, '
                        '"currency": "USD"}], "active_flag": true, "visible_to": 3, '
                        '"owner_id": 123}}'
                    ],
                },
            ),
            types.Tool(
                name="delete_product",
                description="Delete a product from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"product_id": {"type": "integer"}},
                    "required": ["product_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the deletion result",
                    "examples": ['{"success": true, "data": {"id": 1}}'],
                },
            ),
            # Organization Operations
            types.Tool(
                name="create_organization",
                description="Create a new organization in Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "address": {"type": "string"},
                        "visible_to": {"type": "integer", "enum": [1, 3, 5, 7]},
                        "add_time": {"type": "string", "format": "date-time"},
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the created organization data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "name": "Acme Corp", '
                        '"address": "123 Main St", "visible_to": 3, '
                        '"add_time": "2024-03-20 10:00:00"}}'
                    ],
                },
            ),
            types.Tool(
                name="get_organization",
                description="Get a specific organization from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"organization_id": {"type": "integer"}},
                    "required": ["organization_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the organization data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "name": "Acme Corp", '
                        '"address": "123 Main St", "visible_to": 3, '
                        '"add_time": "2024-03-20 10:00:00"}}'
                    ],
                },
            ),
            types.Tool(
                name="update_organization",
                description="Update an organization in Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "organization_id": {"type": "integer"},
                        "name": {"type": "string"},
                        "address": {"type": "string"},
                        "visible_to": {"type": "integer", "enum": [1, 3, 5, 7]},
                    },
                    "required": ["organization_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the updated organization data",
                    "examples": [
                        '{"success": true, "data": {"id": 1, "name": "Acme Corp", '
                        '"address": "123 Main St", "visible_to": 3, '
                        '"add_time": "2024-03-20 10:00:00"}}'
                    ],
                },
            ),
            types.Tool(
                name="delete_organization",
                description="Delete an organization from Pipedrive",
                inputSchema={
                    "type": "object",
                    "properties": {"organization_id": {"type": "integer"}},
                    "required": ["organization_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the deletion result",
                    "examples": ['{"success": true, "data": {"id": 1}}'],
                },
            ),
            # User Operations
            types.Tool(
                name="get_all_users",
                description="Get all users from Pipedrive",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "string",
                    "description": "JSON response containing the list of users",
                    "examples": [
                        '{"id": 2354543, "name": "John Doe", "email": "john@example.com", "lang": 1, "locale": "en_US", "timezone_name": "Asia/Kolkata", "timezone_offset": "+05:30", "default_currency": "USD", "icon_url": null, "active_flag": true, "is_deleted": false, "is_admin": 1, "role_id": 1, "created": "2025-04-30 09:03:50", "has_created_company": true, "is_you": true, "access": [{"app": "sales", "admin": true, "permission_set_id": "08d28770-11f0-8ff0-797a5cc8274d"}, {"app": "global", "admin": true, "permission_set_id": "08d76970-11f0-8ff0-797a5cc8274d"}, {"app": "account_settings", "admin": true, "permission_set_id": "08e12d70-25a2-11f0-797a5cc8274d"}], "phone": null, "modified": "2025-05-01 20:40:54", "last_login": "2025-05-01 20:40:54"}'
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
        """
        Handle Pipedrive tool invocation from the MCP system.

        Args:
            name (str): The name of the tool being called
            arguments (dict | None): Parameters passed to the tool

        Returns:
            list[TextContent]: Output content from tool execution
        """
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if arguments is None:
            arguments = {}

        try:
            pipedrive = await _get_pipedrive_client()

            if name == "create_activity":
                result = pipedrive.create_activity(
                    subject=arguments["subject"],
                    type=arguments["type"],
                    due_date=arguments["due_date"],
                    due_time=arguments.get("due_time"),
                    duration=arguments.get("duration"),
                    user_id=arguments.get("user_id"),
                    deal_id=arguments.get("deal_id"),
                    person_id=arguments.get("person_id"),
                    org_id=arguments.get("org_id"),
                    note=arguments.get("note"),
                )
            elif name == "create_deal":
                result = pipedrive.create_deal(
                    title=arguments["title"],
                    org_id=arguments.get("org_id"),
                    value=arguments.get("value"),
                    currency=arguments.get("currency"),
                    user_id=arguments.get("user_id"),
                    person_id=arguments.get("person_id"),
                    stage_id=arguments.get("stage_id"),
                    status=arguments.get("status"),
                    probability=arguments.get("probability"),
                    expected_close_date=arguments.get("expected_close_date"),
                    visible_to=arguments.get("visible_to"),
                    add_time=arguments.get("add_time"),
                    custom_fields=arguments.get("custom_fields"),
                )
            elif name == "create_lead":
                result = pipedrive.create_lead(
                    title=arguments["title"],
                    person_id=arguments.get("person_id"),
                    organization_id=arguments.get("org_id"),
                    value=arguments.get("value"),
                    owner_id=arguments.get("owner_id"),
                    label_ids=arguments.get("label_ids"),
                    expected_close_date=arguments.get("expected_close_date"),
                    visible_to=arguments.get("visible_to"),
                    was_seen=arguments.get("was_seen"),
                    custom_fields=arguments.get("custom_fields"),
                )
            elif name == "create_note":
                result = pipedrive.create_note(
                    content=arguments["content"],
                    person_id=arguments.get("person_id"),
                    organization_id=arguments.get("organization_id"),
                    deal_id=arguments.get("deal_id"),
                    user_id=arguments.get("user_id"),
                    pinned_to_deal_flag=arguments.get("pinned_to_deal_flag"),
                    pinned_to_organization_flag=arguments.get(
                        "pinned_to_organization_flag"
                    ),
                    pinned_to_person_flag=arguments.get("pinned_to_person_flag"),
                )
            elif name == "create_person":
                result = pipedrive.create_person(
                    name=arguments["name"],
                    email=arguments.get("email"),
                    phone=arguments.get("phone"),
                    org_id=arguments.get("org_id"),
                    custom_fields=arguments.get("custom_fields"),
                )
            elif name == "create_product":
                result = pipedrive.create_product(
                    name=arguments["name"],
                    code=arguments["code"],
                    unit=arguments["unit"],
                    prices=arguments["prices"],
                    active_flag=arguments.get("active_flag", True),
                    visible_to=arguments.get("visible_to", 3),
                    owner_id=arguments.get("owner_id"),
                )
            elif name == "get_all_leads":
                result = pipedrive.get_all_leads(
                    start=arguments.get("start", 0),
                    limit=arguments.get("limit", 100),
                    sort=arguments.get("sort"),
                    status=arguments.get("status"),
                )
            elif name == "get_all_products":
                result = pipedrive.get_all_products(
                    start=arguments.get("start", 0),
                    limit=arguments.get("limit", 100),
                    sort=arguments.get("sort"),
                )
            elif name == "get_lead":
                result = pipedrive.get_lead(arguments["lead_id"])
            elif name == "update_deal":
                result = pipedrive.update_deal(
                    deal_id=arguments["deal_id"],
                    title=arguments.get("title"),
                    value=arguments.get("value"),
                    currency=arguments.get("currency"),
                    status=arguments.get("status"),
                    owner_id=arguments.get("owner_id"),
                    org_id=arguments.get("org_id"),
                    person_id=arguments.get("person_id"),
                    custom_fields=arguments.get("custom_fields"),
                )
            elif name == "update_person":
                result = pipedrive.update_person(
                    person_id=arguments["person_id"],
                    name=arguments.get("name"),
                    email=arguments.get("email"),
                    phone=arguments.get("phone"),
                    org_id=arguments.get("org_id"),
                    custom_fields=arguments.get("custom_fields"),
                )
            elif name == "get_all_users":
                result = pipedrive.get_all_users()
            elif name == "get_persons":
                result = pipedrive.get_all_persons(
                    start=arguments.get("start", 0),
                    limit=arguments.get("limit", 100),
                    sort=arguments.get("sort"),
                )
            elif name == "get_organizations":
                result = pipedrive.get_all_organizations(
                    start=arguments.get("start", 0),
                    limit=arguments.get("limit", 100),
                    sort=arguments.get("sort"),
                )
            elif name == "get_activity":
                result = pipedrive.get_activity(arguments["activity_id"])
            elif name == "update_activity":
                result = pipedrive.update_activity(
                    activity_id=arguments["activity_id"],
                    subject=arguments.get("subject"),
                    type=arguments.get("type"),
                    due_date=arguments.get("due_date"),
                    due_time=arguments.get("due_time"),
                    duration=arguments.get("duration"),
                    user_id=arguments.get("user_id"),
                    deal_id=arguments.get("deal_id"),
                    person_id=arguments.get("person_id"),
                    org_id=arguments.get("org_id"),
                    note=arguments.get("note"),
                )
            elif name == "delete_activity":
                result = pipedrive.delete_activity(arguments["activity_id"])
            elif name == "get_deal":
                result = pipedrive.get_deal(arguments["deal_id"])
            elif name == "delete_deal":
                result = pipedrive.delete_deal(arguments["deal_id"])
            elif name == "delete_lead":
                result = pipedrive.delete_lead(arguments["lead_id"])
            elif name == "get_note":
                result = pipedrive.get_note(arguments["note_id"])
            elif name == "update_note":
                result = pipedrive.update_note(
                    note_id=arguments["note_id"],
                    content=arguments.get("content"),
                    deal_id=arguments.get("deal_id"),
                    person_id=arguments.get("person_id"),
                    org_id=arguments.get("org_id"),
                    user_id=arguments.get("user_id"),
                )
            elif name == "delete_note":
                result = pipedrive.delete_note(arguments["note_id"])
            elif name == "get_person":
                result = pipedrive.get_person(arguments["person_id"])
            elif name == "delete_person":
                result = pipedrive.delete_person(arguments["person_id"])
            elif name == "get_product":
                result = pipedrive.get_product(arguments["product_id"])
            elif name == "update_product":
                result = pipedrive.update_product(
                    product_id=arguments["product_id"],
                    name=arguments.get("name"),
                    code=arguments.get("code"),
                    unit=arguments.get("unit"),
                    prices=arguments.get("prices"),
                    active_flag=arguments.get("active_flag"),
                    visible_to=arguments.get("visible_to"),
                    owner_id=arguments.get("owner_id"),
                )
            elif name == "delete_product":
                result = pipedrive.delete_product(arguments["product_id"])
            elif name == "create_organization":
                result = pipedrive.create_organization(
                    name=arguments["name"],
                    address=arguments.get("address"),
                    visible_to=arguments.get("visible_to"),
                    custom_fields=arguments.get("custom_fields"),
                )
            elif name == "get_organization":
                result = pipedrive.get_organization(arguments["org_id"])
            elif name == "update_organization":
                result = pipedrive.update_organization(
                    org_id=arguments["org_id"],
                    name=arguments.get("name"),
                    address=arguments.get("address"),
                    visible_to=arguments.get("visible_to"),
                    custom_fields=arguments.get("custom_fields"),
                )
            elif name == "delete_organization":
                result = pipedrive.delete_organization(arguments["org_id"])
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            # If result is a dict with a 'data' key that is a list, return one TextContent per item
            if isinstance(result, dict) and isinstance(result.get("data"), list):
                return [
                    TextContent(type="text", text=json.dumps(item, indent=2))
                    for item in result["data"]
                ]
            # If result itself is a list, return one TextContent per item
            elif isinstance(result, list):
                return [
                    TextContent(type="text", text=json.dumps(item, indent=2))
                    for item in result
                ]
            # Otherwise, return a single TextContent
            else:
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(
                f"Error executing tool {name}: {str(e)} {e.__traceback__.tb_lineno}"
            )
            return [TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Define the initialization options for the Pipedrive MCP server.

    Args:
        server_instance (Server): The server instance to describe

    Returns:
        InitializationOptions: MCP-compatible initialization configuration
    """
    return InitializationOptions(
        server_name="pipedrive-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


# Main handler allows users to auth
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
