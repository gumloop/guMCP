import os
import sys
from typing import Optional, Iterable

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path

import stripe
from mcp.types import (
    AnyUrl,
    Resource,
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.stripe.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["read_write"]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_stripe_client(user_id, api_key=None):
    """
    Create a new Stripe client instance using the stored OAuth credentials.

    Args:
        user_id (str): The user ID associated with the credentials.
        api_key (str, optional): Optional override for authentication.

    Returns:
        stripe: Stripe API client with credentials initialized.
    """
    token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    stripe.api_key = token
    return stripe


def create_server(user_id, api_key=None):
    """
    Initialize and configure the Stripe MCP server.

    Args:
        user_id (str): The user ID associated with the current session.
        api_key (str, optional): Optional API key override.

    Returns:
        Server: Configured MCP server instance with registered tools.
    """
    server = Server("stripe-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """
        Return a list of available Stripe tools.

        Returns:
            list[Tool]: List of tool definitions supported by this server.
        """
        return [
            Tool(
                name="list_customers",
                description="List customers from Stripe",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="retrieve_balance",
                description="Retrieve current balance",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="list_subscriptions",
                description="List subscriptions",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="create_payment_intent",
                description="Create a payment intent",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "amount": {"type": "integer"},
                        "currency": {"type": "string"},
                    },
                    "required": ["amount", "currency"],
                },
            ),
            Tool(
                name="update_subscription",
                description="Update a subscription",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subscription_id": {"type": "string"},
                        "fields": {"type": "object"},
                    },
                    "required": ["subscription_id", "fields"],
                },
            ),
            Tool(
                name="list_payment_intents",
                description="List payment intents",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="list_charges",
                description="List charges",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="create_customer",
                description="Create a new customer",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Customer's email address. It's displayed alongside the customer in your dashboard and can be useful for searching and tracking.",
                        },
                        "name": {
                            "type": "string",
                            "description": "The customer's full name or business name.",
                        },
                        "phone": {
                            "type": "string",
                            "description": "The customer's phone number.",
                        },
                        "description": {
                            "type": "string",
                            "description": "An arbitrary string that you can attach to a customer object. It is displayed alongside the customer in the dashboard.",
                        },
                        "address": {
                            "type": "object",
                            "description": "The customer's address. Required if calculating taxes.",
                        },
                        "shipping": {
                            "type": "object",
                            "description": "The customer's shipping information. Appears on invoices emailed to this customer.",
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Set of key-value pairs that you can attach to an object for storing additional information.",
                        },
                        "payment_method": {
                            "type": "string",
                            "description": "The ID of the PaymentMethod to attach to the customer.",
                        },
                        "source": {
                            "type": "string",
                            "description": "When using payment sources created via the Token or Sources APIs, passing source will create a new source object, make it the new customer default source, and delete the old customer default if one exists. If you want to add additional sources instead of replacing the existing default, use the card creation API. Whenever you attach a card to a customer, Stripe will automatically validate the card.",
                        },
                    },
                    "required": ["email"],
                },
            ),
            Tool(
                name="create_invoice",
                description="Create a draft invoice",
                inputSchema={
                    "type": "object",
                    "properties": {"customer": {"type": "string"}},
                    "required": ["customer"],
                },
            ),
            Tool(
                name="list_invoices",
                description="List invoices",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="retrieve_customer",
                description="Retrieve customer info",
                inputSchema={
                    "type": "object",
                    "properties": {"customer_id": {"type": "string"}},
                    "required": ["customer_id"],
                },
            ),
            Tool(
                name="create_product",
                description="Create a new product",
                inputSchema={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            ),
            Tool(
                name="confirm_payment_intent",
                description="Confirm payment intent",
                inputSchema={
                    "type": "object",
                    "properties": {"payment_intent_id": {"type": "string"}},
                    "required": ["payment_intent_id"],
                },
            ),
            Tool(
                name="list_products",
                description="List products",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="cancel_subscription",
                description="Cancel a subscription",
                inputSchema={
                    "type": "object",
                    "properties": {"subscription_id": {"type": "string"}},
                    "required": ["subscription_id"],
                },
            ),
            Tool(
                name="retrieve_subscription",
                description="Retrieve subscription",
                inputSchema={
                    "type": "object",
                    "properties": {"subscription_id": {"type": "string"}},
                    "required": ["subscription_id"],
                },
            ),
            Tool(
                name="create_price",
                description="Create a price for a product",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product": {"type": "string"},
                        "unit_amount": {"type": "integer"},
                        "currency": {"type": "string"},
                        "recurring": {
                            "type": "object",
                            "properties": {
                                "interval": {
                                    "type": "string",
                                    "enum": ["day", "week", "month", "year"],
                                },
                                "interval_count": {"type": "integer"},
                                "meter": {"type": "string"},
                                "usage_type": {
                                    "type": "string",
                                    "enum": ["licensed", "metered"],
                                },
                            },
                            "required": ["interval"],
                        },
                    },
                    "required": ["product", "unit_amount", "currency"],
                },
            ),
            Tool(
                name="create_subscription",
                description="Create subscription for a customer",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "customer": {"type": "string"},
                        "price_id": {"type": "string"},
                    },
                    "required": ["customer", "price_id"],
                },
            ),
            Tool(
                name="update_customer",
                description="Update a customer's information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string"},
                        "fields": {"type": "object"},
                    },
                    "required": ["customer_id", "fields"],
                },
            ),
            Tool(
                name="create_payment_method",
                description="Create a new payment method",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "The type of payment method (e.g., 'card', 'us_bank_account')",
                        },
                        "card": {
                            "type": "object",
                            "properties": {
                                "number": {"type": "string"},
                                "exp_month": {"type": "integer"},
                                "exp_year": {"type": "integer"},
                                "cvc": {"type": "string"},
                            },
                            "required": ["number", "exp_month", "exp_year", "cvc"],
                        },
                        "us_bank_account": {
                            "type": "object",
                            "properties": {
                                "account_holder_type": {
                                    "type": "string",
                                    "enum": ["individual", "company"],
                                },
                                "account_number": {"type": "string"},
                                "routing_number": {"type": "string"},
                            },
                            "required": [
                                "account_holder_type",
                                "account_number",
                                "routing_number",
                            ],
                        },
                        "billing_details": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "address": {
                                    "type": "object",
                                    "properties": {
                                        "line1": {"type": "string"},
                                        "city": {"type": "string"},
                                        "state": {"type": "string"},
                                        "postal_code": {"type": "string"},
                                        "country": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "required": ["type"],
                },
            ),
            Tool(
                name="attach_payment_method",
                description="Attach a payment method to a customer",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "payment_method": {
                            "type": "string",
                            "description": "The ID of the payment method to attach",
                        },
                        "customer_id": {
                            "type": "string",
                            "description": "The ID of the customer to attach the payment method to",
                        },
                        "set_as_default": {
                            "type": "boolean",
                            "description": "Whether to set this as the default payment method",
                        },
                    },
                    "required": ["payment_method", "customer_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """
        Handle Stripe tool invocation from the MCP system.

        Args:
            name (str): The name of the tool being called.
            arguments (dict | None): Parameters passed to the tool.

        Returns:
            list[Union[TextContent, ImageContent, EmbeddedResource]]:
                Output content from tool execution.
        """
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if arguments is None:
            arguments = {}

        stripe = await create_stripe_client(server.user_id, api_key=server.api_key)

        try:
            match name:
                case "list_customers":
                    result = stripe.Customer.list()
                case "retrieve_balance":
                    result = stripe.Balance.retrieve()
                case "list_subscriptions":
                    result = stripe.Subscription.list()
                case "create_payment_intent":
                    result = stripe.PaymentIntent.create(**arguments)
                case "update_subscription":
                    sub_id = arguments.pop("subscription_id")
                    result = stripe.Subscription.modify(
                        sub_id, **arguments.get("fields", {})
                    )
                case "list_payment_intents":
                    result = stripe.PaymentIntent.list()
                case "list_charges":
                    result = stripe.Charge.list()
                case "create_customer":
                    result = stripe.Customer.create(**arguments)
                case "create_invoice":
                    result = stripe.Invoice.create(**arguments)
                case "list_invoices":
                    result = stripe.Invoice.list()
                case "retrieve_customer":
                    result = stripe.Customer.retrieve(arguments["customer_id"])
                case "create_product":
                    result = stripe.Product.create(**arguments)
                case "confirm_payment_intent":
                    result = stripe.PaymentIntent.confirm(
                        arguments["payment_intent_id"]
                    )
                case "list_products":
                    result = stripe.Product.list()
                case "cancel_subscription":
                    result = stripe.Subscription.delete(arguments["subscription_id"])
                case "retrieve_subscription":
                    result = stripe.Subscription.retrieve(arguments["subscription_id"])
                case "create_price":
                    result = stripe.Price.create(**arguments)
                case "create_subscription":
                    result = stripe.Subscription.create(
                        customer=arguments["customer"],
                        items=[{"price": arguments["price_id"]}],
                    )
                case "update_customer":
                    cust_id = arguments.pop("customer_id")
                    result = stripe.Customer.modify(
                        cust_id, **arguments.get("fields", {})
                    )
                case "create_payment_method":
                    result = stripe.PaymentMethod.create(**arguments)
                case "attach_payment_method":
                    payment_method = stripe.PaymentMethod.attach(
                        arguments["payment_method"], customer=arguments["customer_id"]
                    )

                    # If set_as_default is True, update the customer's default payment method
                    if arguments.get("set_as_default", False):
                        stripe.Customer.modify(
                            arguments["customer_id"],
                            invoice_settings={
                                "default_payment_method": arguments["payment_method"]
                            },
                        )

                    result = payment_method
                case _:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

            return [TextContent(type="text", text=str(result))]

        except Exception as e:
            logger.error(f"Stripe API error: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Define the initialization options for the Stripe MCP server.

    Args:
        server_instance (Server): The server instance to describe.

    Returns:
        InitializationOptions: MCP-compatible initialization configuration.
    """
    return InitializationOptions(
        server_name="stripe-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
