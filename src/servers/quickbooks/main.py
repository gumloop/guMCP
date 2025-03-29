#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from typing import Optional, Sequence
from pathlib import Path
import logging
import json
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("quickbooks-server")


# Create server function with simple imports
def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    from mcp.types import (
        AnyUrl,
        Resource,
        TextContent,
        Tool,
        ImageContent,
        EmbeddedResource,
    )
    from mcp.server.lowlevel.helper_types import ReadResourceContents
    from mcp.server import Server

    # Delay importing QuickBooks-specific modules until needed
    server = Server("quickbooks-server")
    server.user_id = user_id
    server.api_key = api_key

    async def get_quickbooks_client():
        """Create and return a QuickBooks client instance"""
        # Import here to avoid top-level import issues
        from src.servers.quickbooks.utils.client import create_quickbooks_client

        return await create_quickbooks_client(server.user_id)

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List QuickBooks resources"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        try:
            resources = []

            # List customers
            customer_resource = Resource(
                uri="quickbooks://customers",
                mimeType="application/json",
                name="Customers",
                description="List of all customers in QuickBooks",
            )
            resources.append(customer_resource)

            # List invoices
            invoice_resource = Resource(
                uri="quickbooks://invoices",
                mimeType="application/json",
                name="Invoices",
                description="List of all invoices in QuickBooks",
            )
            resources.append(invoice_resource)

            # List accounts
            account_resource = Resource(
                uri="quickbooks://accounts",
                mimeType="application/json",
                name="Accounts",
                description="Chart of accounts in QuickBooks",
            )
            resources.append(account_resource)

            # List items/products
            item_resource = Resource(
                uri="quickbooks://items",
                mimeType="application/json",
                name="Items/Products",
                description="List of all items and products in QuickBooks",
            )
            resources.append(item_resource)

            # List bills
            bill_resource = Resource(
                uri="quickbooks://bills",
                mimeType="application/json",
                name="Bills",
                description="List of all bills in QuickBooks",
            )
            resources.append(bill_resource)

            # List payments
            payment_resource = Resource(
                uri="quickbooks://payments",
                mimeType="application/json",
                name="Payments",
                description="List of all payments in QuickBooks",
            )
            resources.append(payment_resource)

            return resources

        except Exception as e:
            logger.error(f"Error listing QuickBooks resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(
        resource_uri: AnyUrl,
        cursor: Optional[str] = None,
    ) -> ReadResourceContents:
        """Read QuickBooks resource contents"""
        try:
            # Import QuickBooks objects only when needed
            import quickbooks.objects.customer
            import quickbooks.objects.invoice
            import quickbooks.objects.account
            import quickbooks.objects.item
            import quickbooks.objects.bill
            import quickbooks.objects.vendor
            import quickbooks.objects.payment

            from src.servers.quickbooks.utils.formatters import (
                format_customer,
                format_invoice,
                format_account,
            )

            Customer = quickbooks.objects.customer.Customer
            Invoice = quickbooks.objects.invoice.Invoice
            Account = quickbooks.objects.account.Account
            Item = quickbooks.objects.item.Item
            Bill = quickbooks.objects.bill.Bill
            Payment = quickbooks.objects.payment.Payment

            # Validate URI format
            if not str(resource_uri).startswith("quickbooks://"):
                raise ValueError("Invalid QuickBooks URI")

            # Extract resource type
            resource_type = str(resource_uri).split("://")[1].lower()

            # Validate resource type
            valid_types = [
                "customers",
                "invoices",
                "accounts",
                "items",
                "bills",
                "payments",
            ]
            if resource_type not in valid_types:
                raise ValueError("Unknown resource type")

            # Get QuickBooks client
            qb_client = await get_quickbooks_client()
            result = []

            if resource_type == "customers":
                # Get customers
                customers = Customer.all(qb=qb_client)
                formatted_customers = [format_customer(c) for c in customers]
                result = formatted_customers

            elif resource_type == "invoices":
                # Get invoices
                invoices = Invoice.all(qb=qb_client)
                formatted_invoices = [format_invoice(i) for i in invoices]
                result = formatted_invoices

            elif resource_type == "accounts":
                # Get accounts
                accounts = Account.all(qb=qb_client)
                formatted_accounts = [format_account(a) for a in accounts]
                result = formatted_accounts

            elif resource_type == "items":
                # Get items/products
                items = Item.all(qb=qb_client)
                formatted_items = [
                    {
                        "id": item.Id,
                        "name": item.Name,
                        "type": item.Type,
                        "price": getattr(item, "UnitPrice", 0),
                    }
                    for item in items
                ]
                result = formatted_items

            elif resource_type == "bills":
                # Get bills
                bills = Bill.all(qb=qb_client)
                formatted_bills = [
                    {
                        "id": bill.Id,
                        "vendor": (
                            getattr(bill.VendorRef, "name", "")
                            if hasattr(bill, "VendorRef")
                            else ""
                        ),
                        "date": getattr(bill, "TxnDate", ""),
                        "due_date": getattr(bill, "DueDate", ""),
                        "total": getattr(bill, "TotalAmt", 0),
                        "balance": getattr(bill, "Balance", 0),
                    }
                    for bill in bills
                ]
                result = formatted_bills

            elif resource_type == "payments":
                # Get payments
                payments = Payment.all(qb=qb_client)
                formatted_payments = [
                    {
                        "id": payment.Id,
                        "customer": (
                            getattr(payment.CustomerRef, "name", "")
                            if hasattr(payment, "CustomerRef")
                            else ""
                        ),
                        "date": getattr(payment, "TxnDate", ""),
                        "amount": getattr(payment, "TotalAmt", 0),
                    }
                    for payment in payments
                ]
                result = formatted_payments

            else:
                raise ValueError(f"Unknown resource type: {resource_type}")

            return ReadResourceContents(
                content=json.dumps(result, indent=2), mime_type="application/json"
            )

        except Exception as e:
            logger.error(f"Error reading QuickBooks resource: {e}")
            return ReadResourceContents(
                content=f"Error: {str(e)}", mime_type="text/plain"
            )

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="search_customers",
                description="Search for customers in QuickBooks",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for customer name, email, or phone",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="analyze_sred",
                description="Analyze expenses for potential SR&ED eligibility",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date for analysis (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date for analysis (YYYY-MM-DD)",
                        },
                        "keywords": {
                            "type": "array",
                            "description": "Additional keywords to search for in transaction descriptions",
                            "items": {"type": "string"},
                            "default": [
                                "research",
                                "development",
                                "experiment",
                                "testing",
                                "prototype",
                                "engineering",
                            ],
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            ),
            Tool(
                name="analyze_cash_flow",
                description="Analyze cash flow trends and patterns",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date for analysis (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date for analysis (YYYY-MM-DD)",
                        },
                        "group_by": {
                            "type": "string",
                            "description": "Group results by 'month' or 'quarter'",
                            "enum": ["month", "quarter"],
                            "default": "month",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            ),
            Tool(
                name="find_duplicate_transactions",
                description="Identify potential duplicate transactions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date for analysis (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date for analysis (YYYY-MM-DD)",
                        },
                        "amount_threshold": {
                            "type": "number",
                            "description": "Minimum amount to consider for duplicate detection",
                            "default": 100,
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            ),
            Tool(
                name="analyze_customer_payment_patterns",
                description="Analyze customer payment behavior and patterns",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "QuickBooks customer ID to analyze",
                        },
                        "months": {
                            "type": "integer",
                            "description": "Number of months to analyze",
                            "default": 12,
                        },
                    },
                    "required": ["customer_id"],
                },
            ),
            Tool(
                name="generate_financial_metrics",
                description="Generate key financial metrics and ratios",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date for analysis (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date for analysis (YYYY-MM-DD)",
                        },
                        "metrics": {
                            "type": "array",
                            "description": "List of metrics to calculate",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "current_ratio",
                                    "quick_ratio",
                                    "debt_to_equity",
                                    "gross_margin",
                                    "operating_margin",
                                    "net_margin",
                                ],
                            },
                            "default": ["current_ratio", "gross_margin", "net_margin"],
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        tool_name: str, arguments: dict | None
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        try:
            logger.info(f"Received tool call request: {tool_name}")
            logger.info(f"Arguments: {arguments}")

            if arguments is None:
                arguments = {}

            if tool_name == "test":
                return [TextContent(type="text", text="Server is working!")]

            # Import tool handlers only when needed to avoid circular imports
            from src.servers.quickbooks.handlers.tools import (
                handle_search_customers,
                handle_analyze_sred,
                handle_analyze_cash_flow,
                handle_find_duplicate_transactions,
                handle_analyze_customer_payment_patterns,
                handle_generate_financial_metrics,
            )

            if tool_name == "search_customers":
                return await handle_search_customers(server, arguments)
            elif tool_name == "analyze_sred":
                return await handle_analyze_sred(server, arguments)
            elif tool_name == "analyze_cash_flow":
                return await handle_analyze_cash_flow(server, arguments)
            elif tool_name == "find_duplicate_transactions":
                return await handle_find_duplicate_transactions(server, arguments)
            elif tool_name == "analyze_customer_payment_patterns":
                return await handle_analyze_customer_payment_patterns(server, arguments)
            elif tool_name == "generate_financial_metrics":
                return await handle_generate_financial_metrics(server, arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        except Exception as e:
            logger.error(f"QuickBooks API error: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


# Server instance creation function
server = create_server


def get_initialization_options(server_instance) -> dict:
    """Get options for server initialization"""
    return {
        "title": "QuickBooks Server for guMCP",
        "description": "Access and analyze QuickBooks financial data",
    }


def get_credentials_path(user_id: str) -> Path:
    """Get the path to the credentials file for a user"""
    config_dir = Path.home() / ".config" / "gumcp" / "quickbooks"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / f"{user_id}.json"


# If this is being run directly, execute the main function
if __name__ == "__main__":
    # Ensure arguments are provided
    if len(sys.argv) < 2:
        print("Usage: python main.py [server|auth]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "server":
        # Run as a standalone server
        import sys

        original_argv = sys.argv
        sys.argv = [original_argv[0], "--server", "quickbooks", "--user-id", "local"]

        from src.servers.local import main

        asyncio.run(main())

        # Restore original argv
        sys.argv = original_argv
    elif command == "auth":
        # Run the authentication flow
        from src.utils.quickbooks.util import authenticate_and_save_credentials
        from intuitlib.enums import Scopes

        authenticate_and_save_credentials(
            "local",
            "quickbooks",
            [Scopes.ACCOUNTING, Scopes.PAYMENT],
        )
    else:
        print(f"Unknown command: {command}")
        print("Usage: python main.py [server|auth]")
        sys.exit(1)
