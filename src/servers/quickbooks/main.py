import os
import sys
from typing import Optional, Iterable
from pathlib import Path
import logging
import json
from datetime import datetime, timedelta

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

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

# Import QuickBooks objects
from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.account import Account
from quickbooks.objects.item import Item
from quickbooks.objects.bill import Bill
from quickbooks.objects.vendor import Vendor
from quickbooks.objects.payment import Payment

# Import local modules using absolute imports
from src.utils.quickbooks.util import authenticate_and_save_credentials, get_credentials
from intuitlib.enums import Scopes

# Import local modules using absolute imports
from src.servers.quickbooks.utils.formatters import format_customer, format_invoice, format_account
from src.servers.quickbooks.handlers.tools import (
    handle_search_customers,
    handle_analyze_sred,
    handle_analyze_cash_flow,
    handle_find_duplicate_transactions,
    handle_analyze_customer_payment_patterns,
    handle_generate_financial_metrics,
)

# Move this import to the top level, after the other imports
from src.servers.quickbooks.utils.client import create_quickbooks_client

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    Scopes.ACCOUNTING,
    Scopes.PAYMENT,
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)

def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    # Remove redundant imports since they're already available from top-level imports
    
    server = Server("quickbooks-server")
    server.user_id = user_id
    server.api_key = api_key

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
            # Validate URI format
            if not str(resource_uri).startswith("quickbooks://"):
                raise ValueError("Invalid QuickBooks URI")

            # Extract resource type
            resource_type = str(resource_uri).split("://")[1].lower()
            
            # Validate resource type
            valid_types = ["customers", "invoices", "accounts", "items", "bills", "payments"]
            if resource_type not in valid_types:
                raise ValueError("Unknown resource type")

            # Get QuickBooks client
            qb_client = await create_quickbooks_client(server.user_id)
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
                formatted_items = [{
                    "id": item.Id,
                    "name": item.Name,
                    "type": item.Type,
                    "price": getattr(item, "UnitPrice", 0),
                } for item in items]
                result = formatted_items
                
            elif resource_type == "bills":
                # Get bills
                bills = Bill.all(qb=qb_client)
                formatted_bills = [{
                    "id": bill.Id,
                    "vendor": getattr(bill.VendorRef, "name", "") if hasattr(bill, "VendorRef") else "",
                    "date": getattr(bill, "TxnDate", ""),
                    "due_date": getattr(bill, "DueDate", ""),
                    "total": getattr(bill, "TotalAmt", 0),
                    "balance": getattr(bill, "Balance", 0),
                } for bill in bills]
                result = formatted_bills
                
            elif resource_type == "payments":
                # Get payments
                payments = Payment.all(qb=qb_client)
                formatted_payments = [{
                    "id": payment.Id,
                    "customer": getattr(payment.CustomerRef, "name", "") if hasattr(payment, "CustomerRef") else "",
                    "date": getattr(payment, "TxnDate", ""),
                    "amount": getattr(payment, "TotalAmt", 0),
                } for payment in payments]
                result = formatted_payments
                
            else:
                raise ValueError(f"Unknown resource type: {resource_type}")

            return ReadResourceContents(
                content=json.dumps(result, indent=2),
                mime_type="application/json"
            )

        except Exception as e:
            logger.error(f"Error reading QuickBooks resource: {e}")
            return ReadResourceContents(content=f"Error: {str(e)}", mime_type="text/plain")

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
                            "default": ["research", "development", "experiment", "testing", "prototype", "engineering"]
                        }
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
                            "default": "month"
                        }
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
                            "default": 100
                        }
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
                            "default": 12
                        }
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
                                "enum": ["current_ratio", "quick_ratio", "debt_to_equity", "gross_margin", "operating_margin", "net_margin"]
                            },
                            "default": ["current_ratio", "gross_margin", "net_margin"]
                        }
                    },
                    "required": ["start_date", "end_date"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        tool_name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        try:
            logger.info(f"Received tool call request: {tool_name}")
            logger.info(f"Arguments: {arguments}")

            if arguments is None:
                arguments = {}

            if tool_name == "test":
                return [TextContent(type="text", text="Server is working!")]

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

server = create_server

def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="quickbooks-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )

# Add this function after the imports
def get_credentials_path(user_id: str) -> Path:
    """Get the path to the credentials file"""
    config_dir = Path.home() / ".config" / "gumcp" / "quickbooks"
    # Create directories if they don't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / f"{user_id}.json"

# Main handler allows users to auth
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("  python main.py server - Start the QuickBooks server")
        print("\nNote: To run the server normally, use the guMCP server framework.")
        print("To run tests, use: python tests/servers/test_runner.py --server=quickbooks")
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "auth":
        user_id = "local"
        # Run authentication flow
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    elif command == "server":
        # Start the server
        import uvicorn
        uvicorn.run(create_server("local"), host="0.0.0.0", port=8001)
    else:
        print(f"Unknown command: {command}")
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("  python main.py server - Start the QuickBooks server")
        print("\nNote: To run the server normally, use the guMCP server framework.")
        print("To run tests, use: python tests/servers/test_runner.py --server=quickbooks")
        sys.exit(1)