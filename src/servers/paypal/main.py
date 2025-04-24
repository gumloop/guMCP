import os
import sys
import logging
import json
import requests
from pathlib import Path
from typing import Optional, List, Dict, TypedDict

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import TextContent

from src.utils.paypal.util import (
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


# Type definitions
class OrderAmount(TypedDict):
    currency_code: str
    value: str


class PurchaseUnit(TypedDict):
    amount: OrderAmount
    description: Optional[str]
    custom_id: Optional[str]
    invoice_id: Optional[str]


class Order(TypedDict):
    id: str
    status: str
    intent: str
    purchase_units: List[PurchaseUnit]
    create_time: str
    links: List[Dict[str, str]]


class OrderResponse(TypedDict):
    order: Order


class PayPalClient:
    """Client for interacting with the PayPal API."""

    def __init__(self, access_token: str):
        """Initialize the PayPal client with an access token."""
        self.access_token = access_token
        self.base_url = "https://api-m.sandbox.paypal.com/"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self, method: str, endpoint: str, params: Dict = None, data: Dict = None
    ) -> Dict:
        """Make a request to the PayPal API."""
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(
            method=method, url=url, headers=self.headers, params=params, json=data
        )
        if response.status_code in [200, 201]:
            return response.json()
        elif response.status_code == 204:
            return {"status": "success"}
        else:
            logger.error(f"Error: {response.status_code} - {response.text}")
            raise Exception(f"Error: {response.status_code} - {response.text}")

    def create_order(
        self,
        intent: str,
        purchase_units: List[Dict],
        payment_source: Optional[Dict] = None,
        application_context: Optional[Dict] = None,
    ) -> OrderResponse:
        """
        Create a new PayPal order.

        Args:
            intent (str): The intent to either capture payment immediately or authorize a payment
            purchase_units (List[Dict]): Array of purchase units
            payment_source (Dict, optional): The payment source definition
            application_context (Dict, optional): Customize the payer experience

        Returns:
            OrderResponse: Order details including approval URL
        """
        data = {"intent": intent, "purchase_units": purchase_units}

        if payment_source:
            data["payment_source"] = payment_source
        if application_context:
            data["application_context"] = application_context

        return self._make_request("POST", "v2/checkout/orders", data=data)

    def get_order(self, order_id: str, fields: Optional[str] = None) -> OrderResponse:
        """
        Get details for an order.

        Args:
            order_id (str): The ID of the order
            fields (str, optional): Comma-separated list of fields to return

        Returns:
            OrderResponse: Order details
        """
        params = {}
        if fields:
            params["fields"] = fields

        return self._make_request(
            "GET", f"v2/checkout/orders/{order_id}", params=params
        )

    def confirm_order(
        self,
        order_id: str,
        payment_source: Dict,
        application_context: Optional[Dict] = None,
    ) -> OrderResponse:
        """
        Confirm the order with the given payment source.

        Args:
            order_id (str): The ID of the order to confirm
            payment_source (Dict): The payment source definition
            application_context (Dict, optional): Customizes the payer confirmation experience

        Returns:
            OrderResponse: Order details after confirmation
        """
        data = {"payment_source": payment_source}

        if application_context:
            data["application_context"] = application_context

        return self._make_request(
            "POST", f"v2/checkout/orders/{order_id}/confirm-payment-source", data=data
        )

    def create_plan(
        self,
        product_id: str,
        name: str,
        description: str,
        billing_cycles: List[Dict],
        payment_preferences: Dict,
        status: str = "ACTIVE",
        quantity_supported: bool = False,
        taxes: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a new billing plan.

        Args:
            product_id (str): The ID of the product created through Catalog Products API
            name (str): The plan name
            description (str): The detailed description of the plan
            billing_cycles (List[Dict]): Array of billing cycles for trial and regular billing
            payment_preferences (Dict): The payment preferences for a subscription
            status (str): The initial state of the plan (CREATED or ACTIVE)
            quantity_supported (bool): Whether you can subscribe with quantity
            taxes (Dict, optional): The tax details

        Returns:
            Dict: The created plan details
        """
        data = {
            "product_id": product_id,
            "name": name,
            "description": description,
            "status": status,
            "billing_cycles": billing_cycles,
            "payment_preferences": payment_preferences,
            "quantity_supported": quantity_supported,
        }

        if taxes:
            data["taxes"] = taxes

        return self._make_request("POST", "v1/billing/plans", data=data)

    def list_plans(
        self,
        product_id: Optional[str] = None,
        page_size: int = 10,
        page: int = 1,
        total_required: bool = False,
    ) -> Dict:
        """
        List billing plans.

        Args:
            product_id (str, optional): Filter by product ID
            page_size (int): Number of items per page (1-20)
            page (int): Page number to return
            total_required (bool): Whether to include total count

        Returns:
            Dict: List of plans and pagination info
        """
        params = {
            "page_size": page_size,
            "page": page,
            "total_required": total_required,
        }

        if product_id:
            params["product_id"] = product_id

        return self._make_request("GET", "v1/billing/plans", params=params)

    def get_plan(self, plan_id: str) -> Dict:
        """
        Get details for a plan.

        Args:
            plan_id (str): The ID of the plan

        Returns:
            Dict: Plan details
        """
        return self._make_request("GET", f"v1/billing/plans/{plan_id}")

    def update_plan(self, plan_id: str, path: str, value: str) -> None:
        """
        Update a plan.

        Args:
            plan_id (str): The ID of the plan to update
            path (str): The path to update (e.g., "/description", "/name", "/payment_preferences/payment_failure_threshold")
            value (str): The new value to set
        """
        url = f"{self.base_url}/v1/billing/plans/{plan_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        data = f'[ {{ "op": "replace", "path": "/{path}", "value": "{value}" }} ]'
        response = requests.patch(url, headers=headers, data=data)
        response.raise_for_status()

    def activate_plan(self, plan_id: str) -> None:
        """
        Activate a plan.

        Args:
            plan_id (str): The ID of the plan to activate
        """
        self._make_request("POST", f"v1/billing/plans/{plan_id}/activate")

    def deactivate_plan(self, plan_id: str) -> None:
        """
        Deactivate a plan.

        Args:
            plan_id (str): The ID of the plan to deactivate
        """
        self._make_request("POST", f"v1/billing/plans/{plan_id}/deactivate")

    def create_product(
        self,
        name: str,
        description: str,
        type: str = "PHYSICAL",
        category: Optional[str] = None,
        image_url: Optional[str] = None,
        home_url: Optional[str] = None,
    ) -> Dict:
        """
        Create a new product.

        Args:
            name (str): The product name
            description (str): The product description
            type (str): The product type (PHYSICAL, DIGITAL, or SERVICE)
            category (str, optional): The product category
            image_url (str, optional): The image URL for the product
            home_url (str, optional): The home page URL for the product

        Returns:
            Dict: The created product details
        """
        data = {"name": name, "description": description, "type": type}

        if category:
            data["category"] = category
        if image_url:
            data["image_url"] = image_url
        if home_url:
            data["home_url"] = home_url

        return self._make_request("POST", "v1/catalogs/products", data=data)

    def list_products(
        self, page_size: int = 10, page: int = 1, total_required: bool = False
    ) -> Dict:
        """
        List products.

        Args:
            page_size (int): Number of items per page (1-20)
            page (int): Page number to return
            total_required (bool): Whether to include total count

        Returns:
            Dict: List of products and pagination info
        """
        params = {
            "page_size": page_size,
            "page": page,
            "total_required": total_required,
        }

        return self._make_request("GET", "v1/catalogs/products", params=params)

    def get_product(self, product_id: str) -> Dict:
        """
        Get details for a product.

        Args:
            product_id (str): The ID of the product

        Returns:
            Dict: Product details
        """
        return self._make_request("GET", f"v1/catalogs/products/{product_id}")

    def update_product(self, product_id: str, path: str, value: str) -> None:
        """
        Update a product.

        Args:
            product_id (str): The ID of the product to update
            path (str): The path to update (e.g., "/description", "/name", "/category")
            value (str): The new value to set
        """
        url = f"{self.base_url}/v1/catalogs/products/{product_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        data = f'[ {{ "op": "replace", "path": "{path}", "value": "{value}" }} ]'
        response = requests.patch(url, headers=headers, data=data)
        response.raise_for_status()

    def search_invoices(
        self,
        page: int = 1,
        page_size: int = 20,
        total_required: bool = False,
        recipient_email: Optional[str] = None,
        recipient_first_name: Optional[str] = None,
        recipient_last_name: Optional[str] = None,
        recipient_business_name: Optional[str] = None,
        invoice_number: Optional[str] = None,
        status: Optional[List[str]] = None,
        reference: Optional[str] = None,
        memo: Optional[str] = None,
        payment_date_range: Optional[Dict] = None,
        archived: Optional[bool] = None,
        fields: Optional[List[str]] = None,
        currency_code: Optional[str] = None,
        total_amount_range: Optional[Dict] = None,
        invoice_date_range: Optional[Dict] = None,
        due_date_range: Optional[Dict] = None,
        creation_date_range: Optional[Dict] = None,
    ) -> Dict:
        """
        Search for invoices based on specified criteria.

        Args:
            page (int): Page number to retrieve (1-1000)
            page_size (int): Number of items per page (1-100)
            total_required (bool): Whether to include total count
            recipient_email (str, optional): Filter by recipient email
            recipient_first_name (str, optional): Filter by recipient first name
            recipient_last_name (str, optional): Filter by recipient last name
            recipient_business_name (str, optional): Filter by recipient business name
            invoice_number (str, optional): Filter by invoice number
            status (List[str], optional): Filter by invoice status
            reference (str, optional): Filter by reference number
            memo (str, optional): Filter by memo
            payment_date_range (Dict, optional): Filter by payment date range
            archived (bool, optional): Filter by archived status
            fields (List[str], optional): Fields to return
            currency_code (str, optional): Filter by currency code
            total_amount_range (Dict, optional): Filter by total amount range
            invoice_date_range (Dict, optional): Filter by invoice date range
            due_date_range (Dict, optional): Filter by due date range
            creation_date_range (Dict, optional): Filter by creation date range

        Returns:
            Dict: Search results containing matching invoices
        """
        data = {"page": page, "page_size": page_size, "total_required": total_required}

        if recipient_email:
            data["recipient_email"] = recipient_email
        if recipient_first_name:
            data["recipient_first_name"] = recipient_first_name
        if recipient_last_name:
            data["recipient_last_name"] = recipient_last_name
        if recipient_business_name:
            data["recipient_business_name"] = recipient_business_name
        if invoice_number:
            data["invoice_number"] = invoice_number
        if status:
            data["status"] = status
        if reference:
            data["reference"] = reference
        if memo:
            data["memo"] = memo
        if payment_date_range:
            data["payment_date_range"] = payment_date_range
        if archived is not None:
            data["archived"] = archived
        if fields:
            data["fields"] = fields
        if currency_code:
            data["currency_code"] = currency_code
        if total_amount_range:
            data["total_amount_range"] = total_amount_range
        if invoice_date_range:
            data["invoice_date_range"] = invoice_date_range
        if due_date_range:
            data["due_date_range"] = due_date_range
        if creation_date_range:
            data["creation_date_range"] = creation_date_range

        return self._make_request("POST", "v2/invoicing/search-invoices", data=data)

    def create_subscription(
        self,
        plan_id: str,
        quantity: Optional[str] = None,
        auto_renewal: bool = False,
        custom_id: Optional[str] = None,
        start_time: Optional[str] = None,
        shipping_amount: Optional[Dict] = None,
        subscriber: Optional[Dict] = None,
        application_context: Optional[Dict] = None,
        plan: Optional[Dict] = None,
        prefer: str = "return=minimal",
        paypal_request_id: Optional[str] = None,
    ) -> Dict:
        """
        Create a new subscription.

        Args:
            plan_id (str): The ID of the plan (26 characters)
            quantity (str, optional): The quantity of the product in the subscription (1-32 characters)
            auto_renewal (bool): Whether the subscription auto-renews after billing cycles complete
            custom_id (str, optional): The custom id for the subscription (1-127 characters)
            start_time (str, optional): The date and time when the subscription started
            shipping_amount (Dict, optional): The shipping charges
            subscriber (Dict, optional): The subscriber request information
            application_context (Dict, optional): Customizes the payer experience
            plan (Dict, optional): An inline plan object to customize the subscription
            prefer (str): The preferred server response format
            paypal_request_id (str, optional): The PayPal request ID

        Returns:
            Dict: Subscription details
        """

        data = {"plan_id": plan_id, "auto_renewal": auto_renewal}

        if quantity:
            data["quantity"] = quantity
        if custom_id:
            data["custom_id"] = custom_id
        if start_time:
            data["start_time"] = start_time
        if shipping_amount:
            data["shipping_amount"] = shipping_amount
        if subscriber:
            data["subscriber"] = subscriber
        if application_context:
            data["application_context"] = application_context
        if plan:
            data["plan"] = plan

        return self._make_request("POST", "v1/billing/subscriptions", data=data)

    def get_subscription(
        self, subscription_id: str, fields: Optional[str] = None
    ) -> Dict:
        """
        Get details for a subscription.

        Args:
            subscription_id (str): The ID of the subscription
            fields (str, optional): List of fields to return in the response (1-100 characters)

        Returns:
            Dict: Subscription details including:
                - ID
                - Plan ID
                - Start time
                - Quantity
                - Shipping amount
                - Subscriber information
                - Billing info
                - Create/update times
                - Status
                - Links
        """
        params = {}
        if fields:
            params["fields"] = fields

        return self._make_request(
            "GET", f"v1/billing/subscriptions/{subscription_id}", params=params
        )


async def create_paypal_client(user_id: str, api_key: str = None) -> PayPalClient:
    """
    Create an authorized PayPal API client.

    Args:
        user_id (str): The user ID associated with the credentials
        api_key (str, optional): Optional override for authentication

    Returns:
        PayPalClient: PayPal API client with credentials initialized
    """
    token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return PayPalClient(token.get("access_token"))


def create_server(user_id: str, api_key: str = None) -> Server:
    """
    Initialize and configure the PayPal MCP server.

    Args:
        user_id (str): The user ID associated with the current session
        api_key (str, optional): Optional API key override

    Returns:
        Server: Configured MCP server instance
    """
    server = Server("paypal-server")

    server.user_id = user_id
    server.api_key = api_key
    server._paypal_client = None

    async def _get_paypal_client() -> PayPalClient:
        """Get or create a PayPal client."""
        if not server._paypal_client:
            server._paypal_client = await create_paypal_client(
                server.user_id, server.api_key
            )
        return server._paypal_client

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Return a list of available PayPal tools.

        Returns:
            list[types.Tool]: List of tool definitions supported by this server
        """
        return [
            types.Tool(
                name="create_order",
                description="Create a new PayPal order",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "intent": {"type": "string", "enum": ["CAPTURE", "AUTHORIZE"]},
                        "purchase_units": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "amount": {
                                        "type": "object",
                                        "properties": {
                                            "currency_code": {"type": "string"},
                                            "value": {"type": "string"},
                                        },
                                        "required": ["currency_code", "value"],
                                    }
                                },
                                "required": ["amount"],
                            },
                        },
                        "payment_source": {"type": "object"},
                        "application_context": {"type": "object"},
                    },
                    "required": ["intent", "purchase_units"],
                },
            ),
            types.Tool(
                name="get_order",
                description="Get details for an order",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                        "fields": {"type": "string"},
                    },
                    "required": ["order_id"],
                },
            ),
            types.Tool(
                name="confirm_order",
                description="Confirm the order with the given payment source",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                        "payment_source": {
                            "type": "object",
                            "properties": {
                                "paypal": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "object",
                                            "properties": {
                                                "given_name": {"type": "string"},
                                                "surname": {"type": "string"},
                                            },
                                        },
                                        "email_address": {"type": "string"},
                                        "experience_context": {"type": "object"},
                                    },
                                }
                            },
                        },
                        "application_context": {"type": "object"},
                    },
                    "required": ["order_id", "payment_source"],
                },
            ),
            types.Tool(
                name="create_plan",
                description="Create a new billing plan",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "billing_cycles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "frequency": {
                                        "type": "object",
                                        "properties": {
                                            "interval_unit": {"type": "string"},
                                            "interval_count": {"type": "integer"},
                                        },
                                    },
                                    "tenure_type": {"type": "string"},
                                    "sequence": {"type": "integer"},
                                    "total_cycles": {"type": "integer"},
                                    "pricing_scheme": {
                                        "type": "object",
                                        "properties": {
                                            "fixed_price": {
                                                "type": "object",
                                                "properties": {
                                                    "value": {"type": "string"},
                                                    "currency_code": {"type": "string"},
                                                },
                                            }
                                        },
                                    },
                                },
                            },
                        },
                        "payment_preferences": {
                            "type": "object",
                            "properties": {
                                "auto_bill_outstanding": {"type": "boolean"},
                                "setup_fee": {
                                    "type": "object",
                                    "properties": {
                                        "value": {"type": "string"},
                                        "currency_code": {"type": "string"},
                                    },
                                },
                                "setup_fee_failure_action": {"type": "string"},
                                "payment_failure_threshold": {"type": "integer"},
                            },
                        },
                        "status": {"type": "string"},
                        "quantity_supported": {"type": "boolean"},
                        "taxes": {
                            "type": "object",
                            "properties": {
                                "percentage": {"type": "string"},
                                "inclusive": {"type": "boolean"},
                            },
                        },
                    },
                    "required": [
                        "product_id",
                        "name",
                        "description",
                        "billing_cycles",
                        "payment_preferences",
                    ],
                },
            ),
            types.Tool(
                name="list_plans",
                description="List billing plans",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "page_size": {"type": "integer"},
                        "page": {"type": "integer"},
                        "total_required": {"type": "boolean"},
                    },
                },
            ),
            types.Tool(
                name="get_plan",
                description="Get details for a plan",
                inputSchema={
                    "type": "object",
                    "properties": {"plan_id": {"type": "string"}},
                    "required": ["plan_id"],
                },
            ),
            types.Tool(
                name="update_plan",
                description="Update a plan",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plan_id": {"type": "string"},
                        "path": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["plan_id", "path", "value"],
                },
            ),
            types.Tool(
                name="activate_plan",
                description="Activate a plan",
                inputSchema={
                    "type": "object",
                    "properties": {"plan_id": {"type": "string"}},
                    "required": ["plan_id"],
                },
            ),
            types.Tool(
                name="deactivate_plan",
                description="Deactivate a plan",
                inputSchema={
                    "type": "object",
                    "properties": {"plan_id": {"type": "string"}},
                    "required": ["plan_id"],
                },
            ),
            types.Tool(
                name="create_product",
                description="Create a new product",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": ["PHYSICAL", "DIGITAL", "SERVICE"],
                        },
                        "category": {"type": "string"},
                        "image_url": {"type": "string"},
                        "home_url": {"type": "string"},
                    },
                    "required": ["name", "description", "Category"],
                },
            ),
            types.Tool(
                name="list_products",
                description="List products",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_size": {"type": "integer"},
                        "page": {"type": "integer"},
                        "total_required": {"type": "boolean"},
                    },
                },
            ),
            types.Tool(
                name="get_product",
                description="Get details for a product",
                inputSchema={
                    "type": "object",
                    "properties": {"product_id": {"type": "string"}},
                    "required": ["product_id"],
                },
            ),
            types.Tool(
                name="update_product",
                description="Update a product",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "path": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["product_id", "path", "value"],
                },
            ),
            types.Tool(
                name="search_invoices",
                description="Search for invoices based on specified criteria",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer", "minimum": 1, "maximum": 1000},
                        "page_size": {"type": "integer", "minimum": 1, "maximum": 100},
                        "total_required": {"type": "boolean"},
                        "recipient_email": {"type": "string", "maxLength": 254},
                        "recipient_first_name": {"type": "string", "maxLength": 140},
                        "recipient_last_name": {"type": "string", "maxLength": 140},
                        "recipient_business_name": {"type": "string", "maxLength": 300},
                        "invoice_number": {"type": "string", "maxLength": 25},
                        "status": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "DRAFT",
                                    "SENT",
                                    "SCHEDULED",
                                    "PAID",
                                    "MARKED_AS_PAID",
                                    "CANCELLED",
                                    "REFUNDED",
                                    "PARTIALLY_PAID",
                                    "PARTIALLY_REFUNDED",
                                    "MARKED_AS_REFUNDED",
                                    "UNPAID",
                                    "PAYMENT_PENDING",
                                ],
                            },
                            "maxItems": 5,
                        },
                        "reference": {"type": "string", "maxLength": 120},
                        "memo": {"type": "string", "maxLength": 500},
                        "payment_date_range": {"type": "object"},
                        "archived": {"type": "boolean"},
                        "fields": {"type": "array", "items": {"type": "string"}},
                        "currency_code": {
                            "type": "string",
                            "minLength": 3,
                            "maxLength": 3,
                        },
                        "total_amount_range": {"type": "object"},
                        "invoice_date_range": {"type": "object"},
                        "due_date_range": {"type": "object"},
                        "creation_date_range": {"type": "object"},
                    },
                },
            ),
            types.Tool(
                name="create_subscription",
                description="Create a new subscription",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plan_id": {"type": "string", "minLength": 26, "maxLength": 26},
                        "quantity": {"type": "string", "minLength": 1, "maxLength": 32},
                        "auto_renewal": {"type": "boolean"},
                        "custom_id": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 127,
                        },
                        "start_time": {
                            "type": "string",
                            "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|3[0-1])T(2[0-3]|[01][0-9]):[0-5][0-9]:[0-5][0-9](\\.[0-9]{1,3})?Z$",
                        },
                        "shipping_amount": {"type": "object"},
                        "subscriber": {"type": "object"},
                        "application_context": {"type": "object"},
                        "plan": {"type": "object"},
                        "prefer": {
                            "type": "string",
                            "enum": ["return=minimal", "return=representation"],
                        },
                        "paypal_request_id": {"type": "string"},
                    },
                    "required": ["plan_id"],
                },
            ),
            types.Tool(
                name="get_subscription",
                description="Get details for a subscription",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subscription_id": {"type": "string"},
                        "fields": {"type": "string", "minLength": 1, "maxLength": 100},
                    },
                    "required": ["subscription_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
        """
        Handle PayPal tool invocation from the MCP system.

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

        paypal = await _get_paypal_client()

        try:
            if name == "create_order":
                result = paypal.create_order(
                    intent=arguments["intent"],
                    purchase_units=arguments["purchase_units"],
                    payment_source=arguments.get("payment_source"),
                    application_context=arguments.get("application_context"),
                )
                # Add approval URL to the response
                for link in result.get("links", []):
                    if link.get("rel") == "approve":
                        result["approval_url"] = link.get("href")
                        break
            elif name == "get_order":
                result = paypal.get_order(
                    order_id=arguments["order_id"], fields=arguments.get("fields")
                )

            elif name == "confirm_order":
                result = paypal.confirm_order(
                    order_id=arguments["order_id"],
                    payment_source=arguments["payment_source"],
                    application_context=arguments.get("application_context"),
                )
            elif name == "create_plan":
                result = paypal.create_plan(
                    product_id=arguments["product_id"],
                    name=arguments["name"],
                    description=arguments["description"],
                    billing_cycles=arguments["billing_cycles"],
                    payment_preferences=arguments["payment_preferences"],
                    status=arguments.get("status", "ACTIVE"),
                    quantity_supported=arguments.get("quantity_supported", False),
                    taxes=arguments.get("taxes"),
                )
            elif name == "list_plans":
                result = paypal.list_plans(
                    product_id=arguments.get("product_id"),
                    page_size=arguments.get("page_size", 10),
                    page=arguments.get("page", 1),
                    total_required=arguments.get("total_required", False),
                )
            elif name == "get_plan":
                result = paypal.get_plan(arguments["plan_id"])
            elif name == "update_plan":
                paypal.update_plan(
                    plan_id=arguments["plan_id"],
                    path=arguments["path"],
                    value=arguments["value"],
                )
                result = {"success": True, "message": "Plan updated successfully"}
            elif name == "activate_plan":
                paypal.activate_plan(arguments["plan_id"])
                result = {"success": True, "message": "Plan activated successfully"}
            elif name == "deactivate_plan":
                paypal.deactivate_plan(arguments["plan_id"])
                result = {"success": True, "message": "Plan deactivated successfully"}
            elif name == "create_product":
                result = paypal.create_product(
                    name=arguments["name"],
                    description=arguments["description"],
                    type=arguments.get("type", "PHYSICAL"),
                    category=arguments.get("category"),
                    image_url=arguments.get("image_url"),
                    home_url=arguments.get("home_url"),
                )
            elif name == "list_products":
                result = paypal.list_products(
                    page_size=arguments.get("page_size", 10),
                    page=arguments.get("page", 1),
                    total_required=arguments.get("total_required", False),
                )
            elif name == "get_product":
                result = paypal.get_product(arguments["product_id"])
            elif name == "update_product":
                paypal.update_product(
                    product_id=arguments["product_id"],
                    path="/" + arguments["path"],
                    value=arguments["value"],
                )
                result = {"success": True, "message": "Product updated successfully"}
            elif name == "search_invoices":
                result = paypal.search_invoices(
                    page=arguments.get("page", 1),
                    page_size=arguments.get("page_size", 20),
                    total_required=arguments.get("total_required", False),
                    recipient_email=arguments.get("recipient_email"),
                    recipient_first_name=arguments.get("recipient_first_name"),
                    recipient_last_name=arguments.get("recipient_last_name"),
                    recipient_business_name=arguments.get("recipient_business_name"),
                    invoice_number=arguments.get("invoice_number"),
                    status=arguments.get("status"),
                    reference=arguments.get("reference"),
                    memo=arguments.get("memo"),
                    payment_date_range=arguments.get("payment_date_range"),
                    archived=arguments.get("archived"),
                    fields=arguments.get("fields"),
                    currency_code=arguments.get("currency_code"),
                    total_amount_range=arguments.get("total_amount_range"),
                    invoice_date_range=arguments.get("invoice_date_range"),
                    due_date_range=arguments.get("due_date_range"),
                    creation_date_range=arguments.get("creation_date_range"),
                )
            elif name == "create_subscription":
                result = paypal.create_subscription(
                    plan_id=arguments["plan_id"],
                    quantity=arguments.get("quantity"),
                    auto_renewal=arguments.get("auto_renewal", False),
                    custom_id=arguments.get("custom_id"),
                    start_time=arguments.get("start_time"),
                    shipping_amount=arguments.get("shipping_amount"),
                    subscriber=arguments.get("subscriber"),
                    application_context=arguments.get("application_context"),
                    plan=arguments.get("plan"),
                    prefer=arguments.get("prefer", "return=minimal"),
                    paypal_request_id=arguments.get("paypal_request_id"),
                )
            elif name == "get_subscription":
                result = paypal.get_subscription(
                    subscription_id=arguments["subscription_id"],
                    fields=arguments.get("fields"),
                )

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Define the initialization options for the PayPal MCP server.

    Args:
        server_instance (Server): The server instance to describe

    Returns:
        InitializationOptions: MCP-compatible initialization configuration
    """
    return InitializationOptions(
        server_name="paypal-server",
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
        # Run authentication flow
        import asyncio

        asyncio.run(authenticate_and_save_credentials(user_id, SERVICE_NAME))
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
