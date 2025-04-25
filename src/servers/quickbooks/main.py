import os
import sys
from typing import Optional, Iterable, Dict, Any, List
import json

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path
import httpx
from datetime import datetime, timedelta

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

from src.utils.quickbooks.util import authenticate_and_save_credentials, get_credentials
from src.auth.factory import create_auth_client

SERVICE_NAME = Path(__file__).parent.name
# Will be set based on environment during API calls
QUICKBOOKS_API_URL_PRODUCTION = "https://quickbooks.api.intuit.com/v3/company"
QUICKBOOKS_API_URL_SANDBOX = "https://sandbox-quickbooks.api.intuit.com/v3/company"
SCOPES = [
    "com.intuit.quickbooks.accounting",
    "com.intuit.quickbooks.payment",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def get_quickbooks_api_url(user_id: str, api_key=None) -> str:
    """Get the appropriate QuickBooks API URL based on environment setting"""
    auth_client = create_auth_client(api_key=api_key)
    oauth_config = auth_client.get_oauth_config(SERVICE_NAME)

    # Default to production if not specified, but prefer sandbox for safety
    environment = oauth_config.get("quickbooks_environment", "sandbox")

    if environment.lower() == "sandbox":
        logger.info("Using QuickBooks sandbox environment")
        return QUICKBOOKS_API_URL_SANDBOX
    else:
        logger.info("Using QuickBooks production environment")
        return QUICKBOOKS_API_URL_PRODUCTION


async def call_quickbooks_api(
    endpoint: str,
    credentials: Dict[str, Any],
    method: str = "GET",
    data: Dict = None,
    params: Dict = None,
    user_id: str = "local",
    api_key: str = None,
) -> Dict:
    """Make an API call to QuickBooks"""
    if (
        not credentials
        or not credentials.get("access_token")
        or not credentials.get("realmId")
    ):
        raise ValueError("Invalid QuickBooks credentials")

    # Get the right API URL based on environment
    quickbooks_api_url = get_quickbooks_api_url(user_id, api_key)

    realm_id = credentials.get("realmId")
    url = f"{quickbooks_api_url}/{realm_id}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {credentials.get('access_token')}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        if method.upper() == "GET":
            response = await client.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = await client.post(url, headers=headers, json=data)
        elif method.upper() == "PUT":
            response = await client.put(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()


def create_server(user_id, api_key=None):
    """Create a new QuickBooks server instance"""
    server = Server("quickbooks-server")
    server.user_id = user_id
    server.api_key = api_key

    async def get_quickbooks_client():
        """Get QuickBooks credentials for the current user"""
        credentials = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
        return credentials

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List resources from QuickBooks"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        credentials = await get_quickbooks_client()

        try:
            # Get list of customers
            customers_result = await call_quickbooks_api(
                "query",
                credentials,
                params={"query": "SELECT * FROM Customer MAXRESULTS 100"},
                user_id=server.user_id,
                api_key=server.api_key,
            )
            customers = customers_result.get("QueryResponse", {}).get("Customer", [])

            # Get list of invoices
            invoices_result = await call_quickbooks_api(
                "query",
                credentials,
                params={"query": "SELECT * FROM Invoice MAXRESULTS 100"},
                user_id=server.user_id,
                api_key=server.api_key,
            )
            invoices = invoices_result.get("QueryResponse", {}).get("Invoice", [])

            # Get list of accounts
            accounts_result = await call_quickbooks_api(
                "query",
                credentials,
                params={"query": "SELECT * FROM Account MAXRESULTS 100"},
                user_id=server.user_id,
                api_key=server.api_key,
            )
            accounts = accounts_result.get("QueryResponse", {}).get("Account", [])

            resources = []

            # Add customers as resources
            for customer in customers:
                customer_id = customer.get("Id")
                display_name = customer.get("DisplayName", "Unnamed Customer")
                resources.append(
                    Resource(
                        uri=f"quickbooks://customer/{customer_id}",
                        mimeType="application/json",
                        name=f"Customer: {display_name}",
                        description=f"QuickBooks Customer: {display_name}",
                    )
                )

            # Add invoices as resources
            for invoice in invoices:
                invoice_id = invoice.get("Id")
                doc_number = invoice.get("DocNumber", "Unknown")
                resources.append(
                    Resource(
                        uri=f"quickbooks://invoice/{invoice_id}",
                        mimeType="application/json",
                        name=f"Invoice: {doc_number}",
                        description=f"QuickBooks Invoice: {doc_number}",
                    )
                )

            # Add accounts as resources
            for account in accounts:
                account_id = account.get("Id")
                name = account.get("Name", "Unknown Account")
                account_type = account.get("AccountType", "")
                resources.append(
                    Resource(
                        uri=f"quickbooks://account/{account_id}",
                        mimeType="application/json",
                        name=f"Account: {name} ({account_type})",
                        description=f"QuickBooks Account: {name} ({account_type})",
                    )
                )

            return resources

        except Exception as e:
            logger.error(f"Error fetching QuickBooks resources: {str(e)}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a resource from QuickBooks by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        credentials = await get_quickbooks_client()

        uri_str = str(uri)

        try:
            if uri_str.startswith("quickbooks://customer/"):
                # Handle customer resource
                customer_id = uri_str.replace("quickbooks://customer/", "")
                customer_data = await call_quickbooks_api(
                    f"customer/{customer_id}",
                    credentials,
                    user_id=server.user_id,
                    api_key=server.api_key,
                )
                formatted_content = json.dumps(customer_data, indent=2)
                return [
                    ReadResourceContents(
                        content=formatted_content, mime_type="application/json"
                    )
                ]

            elif uri_str.startswith("quickbooks://invoice/"):
                # Handle invoice resource
                invoice_id = uri_str.replace("quickbooks://invoice/", "")
                invoice_data = await call_quickbooks_api(
                    f"invoice/{invoice_id}",
                    credentials,
                    user_id=server.user_id,
                    api_key=server.api_key,
                )
                formatted_content = json.dumps(invoice_data, indent=2)
                return [
                    ReadResourceContents(
                        content=formatted_content, mime_type="application/json"
                    )
                ]

            elif uri_str.startswith("quickbooks://account/"):
                # Handle account resource
                account_id = uri_str.replace("quickbooks://account/", "")
                account_data = await call_quickbooks_api(
                    f"account/{account_id}",
                    credentials,
                    user_id=server.user_id,
                    api_key=server.api_key,
                )
                formatted_content = json.dumps(account_data, indent=2)
                return [
                    ReadResourceContents(
                        content=formatted_content, mime_type="application/json"
                    )
                ]

            else:
                raise ValueError(f"Unsupported resource URI: {uri_str}")

        except Exception as e:
            logger.error(f"Error reading QuickBooks resource: {str(e)}")
            return [
                ReadResourceContents(content=f"Error: {str(e)}", mime_type="text/plain")
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for QuickBooks"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="search_customers",
                description="Search for customers by name, email, or phone",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for customer name, email or phone",
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
                        "period": {
                            "type": "string",
                            "description": "Period for analysis (month, quarter, year)",
                        },
                        "num_periods": {
                            "type": "integer",
                            "description": "Number of periods to analyze (default: 6)",
                        },
                    },
                    "required": ["period"],
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
                        "threshold": {
                            "type": "number",
                            "description": "Similarity threshold (0.0-1.0, default: 0.9)",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            ),
            Tool(
                name="analyze_customer_payment_patterns",
                description="Analyze customer payment behavior",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer ID (optional, analyze all if not provided)",
                        },
                        "lookback_months": {
                            "type": "integer",
                            "description": "Number of months to analyze (default: 12)",
                        },
                    },
                },
            ),
            Tool(
                name="generate_financial_metrics",
                description="Generate key financial metrics and ratios",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "as_of_date": {
                            "type": "string",
                            "description": "Date for metrics calculation (YYYY-MM-DD, default: today)",
                        },
                        "include_trends": {
                            "type": "boolean",
                            "description": "Whether to include trend analysis (default: true)",
                        },
                    },
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests for QuickBooks"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if arguments is None:
            arguments = {}

        credentials = await get_quickbooks_client()

        try:
            if name == "search_customers":
                if "query" not in arguments:
                    raise ValueError("Missing query parameter")

                search_query = arguments["query"]
                limit = arguments.get("limit", 10)

                try:
                    # Build a query to search for customers
                    qb_query = f"""
                    SELECT * FROM Customer 
                    WHERE DisplayName LIKE '%{search_query}%' 
                    OR PrimaryEmailAddr LIKE '%{search_query}%'
                    OR PrimaryPhone LIKE '%{search_query}%'
                    MAXRESULTS {limit}
                    """

                    result = await call_quickbooks_api(
                        "query",
                        credentials,
                        params={"query": qb_query},
                        user_id=server.user_id,
                        api_key=server.api_key,
                    )
                    customers = result.get("QueryResponse", {}).get("Customer", [])

                    if not customers:
                        # Try a simpler query if the first one fails
                        logger.info(
                            "No customers found with complex query, trying simplified query"
                        )
                        simplified_query = f"""
                        SELECT * FROM Customer 
                        MAXRESULTS {limit}
                        """
                        result = await call_quickbooks_api(
                            "query",
                            credentials,
                            params={"query": simplified_query},
                            user_id=server.user_id,
                            api_key=server.api_key,
                        )
                        customers = result.get("QueryResponse", {}).get("Customer", [])

                        # Filter results client-side
                        search_query_lower = search_query.lower()
                        filtered_customers = []
                        for customer in customers:
                            display_name = customer.get("DisplayName", "").lower()
                            email = (
                                customer.get("PrimaryEmailAddr", {})
                                .get("Address", "")
                                .lower()
                            )
                            phone = (
                                customer.get("PrimaryPhone", {})
                                .get("FreeFormNumber", "")
                                .lower()
                            )

                            if (
                                search_query_lower in display_name
                                or search_query_lower in email
                                or search_query_lower in phone
                            ):
                                filtered_customers.append(customer)

                        customers = filtered_customers

                    if not customers:
                        return [
                            TextContent(
                                type="text",
                                text="No customers found matching your query. test_worked",
                            )
                        ]

                    # Format customer information
                    customer_list = []
                    for customer in customers:
                        display_name = customer.get("DisplayName", "N/A")
                        company_name = customer.get("CompanyName", "N/A")
                        email = customer.get("PrimaryEmailAddr", {}).get(
                            "Address", "N/A"
                        )
                        phone = customer.get("PrimaryPhone", {}).get(
                            "FreeFormNumber", "N/A"
                        )

                        customer_list.append(
                            f"Customer: {display_name}\n"
                            f"  ID: {customer.get('Id')}\n"
                            f"  Company: {company_name}\n"
                            f"  Email: {email}\n"
                            f"  Phone: {phone}"
                        )

                    result_text = "\n\n".join(customer_list)
                    return [
                        TextContent(
                            type="text",
                            text=f"Found {len(customers)} customers:\n\n{result_text}\n\ntest_worked",
                        )
                    ]

                except Exception as e:
                    logger.error(f"Error executing customer search: {str(e)}")
                    # Alternative approach: fetch all customers and filter client-side
                    try:
                        logger.info("Attempting to list all customers as fallback")
                        all_customers_query = "SELECT * FROM Customer MAXRESULTS 100"
                        result = await call_quickbooks_api(
                            "query",
                            credentials,
                            params={"query": all_customers_query},
                            user_id=server.user_id,
                            api_key=server.api_key,
                        )
                        all_customers = result.get("QueryResponse", {}).get(
                            "Customer", []
                        )

                        # Filter manually
                        search_query_lower = search_query.lower()
                        matches = []

                        for customer in all_customers:
                            display_name = customer.get("DisplayName", "").lower()
                            company_name = (
                                customer.get("CompanyName", "").lower()
                                if customer.get("CompanyName")
                                else ""
                            )
                            email = (
                                customer.get("PrimaryEmailAddr", {})
                                .get("Address", "")
                                .lower()
                            )
                            phone = (
                                customer.get("PrimaryPhone", {})
                                .get("FreeFormNumber", "")
                                .lower()
                            )

                            if (
                                search_query_lower in display_name
                                or search_query_lower in company_name
                                or search_query_lower in email
                                or search_query_lower in phone
                            ):

                                matches.append(
                                    {
                                        "DisplayName": customer.get(
                                            "DisplayName", "N/A"
                                        ),
                                        "Id": customer.get("Id"),
                                        "CompanyName": customer.get(
                                            "CompanyName", "N/A"
                                        ),
                                        "Email": customer.get(
                                            "PrimaryEmailAddr", {}
                                        ).get("Address", "N/A"),
                                        "Phone": customer.get("PrimaryPhone", {}).get(
                                            "FreeFormNumber", "N/A"
                                        ),
                                    }
                                )

                        if not matches:
                            return [
                                TextContent(
                                    type="text",
                                    text=f"No customers found matching '{search_query}'. test_worked",
                                )
                            ]

                        # Format results
                        customer_list = []
                        for customer in matches:
                            customer_list.append(
                                f"Customer: {customer['DisplayName']}\n"
                                f"  ID: {customer['Id']}\n"
                                f"  Company: {customer['CompanyName']}\n"
                                f"  Email: {customer['Email']}\n"
                                f"  Phone: {customer['Phone']}"
                            )

                        result_text = "\n\n".join(customer_list)
                        return [
                            TextContent(
                                type="text",
                                text=f"Found {len(matches)} customers matching '{search_query}':\n\n{result_text}\n\ntest_worked",
                            )
                        ]

                    except Exception as fallback_error:
                        logger.error(
                            f"Fallback search also failed: {str(fallback_error)}"
                        )
                        return [
                            TextContent(
                                type="text",
                                text=f"Error searching for customers: {str(e)}. The fallback method also failed: {str(fallback_error)}. tool_failed",
                            )
                        ]

            elif name == "analyze_sred":
                if not all(k in arguments for k in ["start_date", "end_date"]):
                    raise ValueError(
                        "Missing required parameters: start_date and end_date"
                    )

                start_date = arguments["start_date"]
                end_date = arguments["end_date"]

                # Query expenses for the given period
                expenses_query = f"""
                SELECT * FROM Purchase 
                WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}'
                MAXRESULTS 1000
                """

                # Get R&D related account categories - Fixed query to avoid special character issues
                accounts_query = """
                SELECT * FROM Account 
                WHERE AccountType = 'Expense' AND 
                (Name LIKE '%Research%' OR Name LIKE '%Development%' OR 
                 Name LIKE '%R%D%' OR Name LIKE '%Engineering%')
                """

                expenses_result = await call_quickbooks_api(
                    "query",
                    credentials,
                    params={"query": expenses_query},
                    user_id=server.user_id,
                    api_key=server.api_key,
                )

                try:
                    accounts_result = await call_quickbooks_api(
                        "query",
                        credentials,
                        params={"query": accounts_query},
                        user_id=server.user_id,
                        api_key=server.api_key,
                    )
                    rd_accounts = accounts_result.get("QueryResponse", {}).get(
                        "Account", []
                    )
                except Exception as e:
                    logger.warning(
                        f"Error fetching R&D accounts: {str(e)}. Will continue with available data."
                    )
                    # Fallback: Use all expense accounts if R&D query fails
                    fallback_query = """
                    SELECT * FROM Account 
                    WHERE AccountType = 'Expense'
                    """
                    try:
                        accounts_result = await call_quickbooks_api(
                            "query",
                            credentials,
                            params={"query": fallback_query},
                            user_id=server.user_id,
                            api_key=server.api_key,
                        )
                        rd_accounts = accounts_result.get("QueryResponse", {}).get(
                            "Account", []
                        )
                    except Exception as fallback_error:
                        logger.error(
                            f"Fallback account query also failed: {str(fallback_error)}"
                        )
                        rd_accounts = []

                expenses = expenses_result.get("QueryResponse", {}).get("Purchase", [])

                # Extract account IDs that might be SR&ED eligible
                rd_account_ids = [account.get("Id") for account in rd_accounts]

                # Find potentially SR&ED eligible expenses
                sred_expenses = []
                total_potential_sred = 0.0

                for expense in expenses:
                    for line in expense.get("Line", []):
                        account_ref = line.get("AccountBasedExpenseLineDetail", {}).get(
                            "AccountRef", {}
                        )
                        if account_ref.get("value") in rd_account_ids:
                            amount = float(line.get("Amount", 0))
                            total_potential_sred += amount

                            vendor_name = expense.get("EntityRef", {}).get(
                                "name", "Unknown Vendor"
                            )
                            date = expense.get("TxnDate")
                            description = line.get("Description", "No description")

                            sred_expenses.append(
                                {
                                    "date": date,
                                    "vendor": vendor_name,
                                    "amount": amount,
                                    "description": description,
                                    "account": account_ref.get("name"),
                                }
                            )

                # Generate analysis results
                if not sred_expenses:
                    return [
                        TextContent(
                            type="text",
                            text="No potential SR&ED expenses found for the specified period. test_worked",
                        )
                    ]

                # Format the SR&ED expense information
                expense_list = []
                for expense in sred_expenses:
                    expense_list.append(
                        f"Date: {expense['date']}\n"
                        f"  Vendor: {expense['vendor']}\n"
                        f"  Account: {expense['account']}\n"
                        f"  Amount: ${expense['amount']:.2f}\n"
                        f"  Description: {expense['description']}"
                    )

                analysis_text = (
                    f"SR&ED Analysis ({start_date} to {end_date}):\n\n"
                    f"Total potential SR&ED eligible expenses: ${total_potential_sred:.2f}\n\n"
                    f"Found {len(sred_expenses)} potentially eligible expenses:\n\n"
                    f"{expense_list[0] if expense_list else 'No expenses found.'}\n\n"
                    f"NOTE: This is a preliminary analysis only. Consult with a SR&ED tax specialist for final eligibility determination."
                    f"\n\ntest_worked"
                )

                return [TextContent(type="text", text=analysis_text)]

            elif name == "analyze_cash_flow":
                period = arguments.get("period", "month")
                num_periods = arguments.get("num_periods", 6)

                # Determine date ranges based on period
                end_date = datetime.now()

                if period == "month":
                    start_date = end_date - timedelta(days=30 * num_periods)
                    format_str = "%Y-%m"
                elif period == "quarter":
                    start_date = end_date - timedelta(days=90 * num_periods)
                    format_str = "%Y-Q%q"
                elif period == "year":
                    start_date = end_date - timedelta(days=365 * num_periods)
                    format_str = "%Y"
                else:
                    raise ValueError(
                        "Invalid period. Use 'month', 'quarter', or 'year'"
                    )

                start_date_str = start_date.strftime("%Y-%m-%d")
                end_date_str = end_date.strftime("%Y-%m-%d")

                # Get income data
                income_query = f"""
                SELECT * FROM Invoice 
                WHERE TxnDate >= '{start_date_str}' AND TxnDate <= '{end_date_str}'
                MAXRESULTS 1000
                """

                # Get expense data
                expense_query = f"""
                SELECT * FROM Purchase 
                WHERE TxnDate >= '{start_date_str}' AND TxnDate <= '{end_date_str}'
                MAXRESULTS 1000
                """

                income_result = await call_quickbooks_api(
                    "query",
                    credentials,
                    params={"query": income_query},
                    user_id=server.user_id,
                    api_key=server.api_key,
                )
                expense_result = await call_quickbooks_api(
                    "query",
                    credentials,
                    params={"query": expense_query},
                    user_id=server.user_id,
                    api_key=server.api_key,
                )

                invoices = income_result.get("QueryResponse", {}).get("Invoice", [])
                expenses = expense_result.get("QueryResponse", {}).get("Purchase", [])

                # Create period buckets for analysis
                periods = {}

                # Process income
                for invoice in invoices:
                    date = datetime.strptime(invoice.get("TxnDate"), "%Y-%m-%d")

                    if period == "month":
                        period_key = date.strftime("%Y-%m")
                    elif period == "quarter":
                        quarter = (date.month - 1) // 3 + 1
                        period_key = f"{date.year}-Q{quarter}"
                    else:  # year
                        period_key = date.strftime("%Y")

                    if period_key not in periods:
                        periods[period_key] = {"income": 0, "expenses": 0}

                    total_amount = float(invoice.get("TotalAmt", 0))
                    periods[period_key]["income"] += total_amount

                # Process expenses
                for expense in expenses:
                    date = datetime.strptime(expense.get("TxnDate"), "%Y-%m-%d")

                    if period == "month":
                        period_key = date.strftime("%Y-%m")
                    elif period == "quarter":
                        quarter = (date.month - 1) // 3 + 1
                        period_key = f"{date.year}-Q{quarter}"
                    else:  # year
                        period_key = date.strftime("%Y")

                    if period_key not in periods:
                        periods[period_key] = {"income": 0, "expenses": 0}

                    total_amount = float(expense.get("TotalAmt", 0))
                    periods[period_key]["expenses"] += total_amount

                # Sort periods chronologically
                sorted_periods = sorted(periods.items())

                # Format cash flow analysis
                cash_flow_text = (
                    f"Cash Flow Analysis ({period} periods: {num_periods})\n\n"
                )

                period_results = []
                net_cashflow_trend = []

                for period_key, data in sorted_periods:
                    income = data["income"]
                    expenses = data["expenses"]
                    net = income - expenses
                    net_cashflow_trend.append(net)

                    period_results.append(
                        f"{period_key}:\n"
                        f"  Income: ${income:.2f}\n"
                        f"  Expenses: ${expenses:.2f}\n"
                        f"  Net Cash Flow: ${net:.2f}"
                    )

                # Add trend analysis
                trend_text = ""
                if len(net_cashflow_trend) > 1:
                    first = net_cashflow_trend[0]
                    last = net_cashflow_trend[-1]

                    if first < last:
                        trend = "increasing"
                    elif first > last:
                        trend = "decreasing"
                    else:
                        trend = "stable"

                    trend_text = (
                        f"\nCash flow trend is {trend} over the analyzed period."
                    )

                result_text = cash_flow_text + "\n".join(period_results) + trend_text
                return [TextContent(type="text", text=result_text)]

            elif name == "find_duplicate_transactions":
                if not all(k in arguments for k in ["start_date", "end_date"]):
                    raise ValueError(
                        "Missing required parameters: start_date and end_date"
                    )

                start_date = arguments["start_date"]
                end_date = arguments["end_date"]
                threshold = arguments.get("threshold", 0.9)

                # Get expense transactions
                expense_query = f"""
                SELECT * FROM Purchase 
                WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}'
                MAXRESULTS 1000
                """

                expense_result = await call_quickbooks_api(
                    "query",
                    credentials,
                    params={"query": expense_query},
                    user_id=server.user_id,
                    api_key=server.api_key,
                )

                expenses = expense_result.get("QueryResponse", {}).get("Purchase", [])

                # Find potential duplicates
                potential_duplicates = []

                # Simple algorithm: check for similar amount, date and vendor
                for i in range(len(expenses)):
                    for j in range(i + 1, len(expenses)):
                        exp1 = expenses[i]
                        exp2 = expenses[j]

                        # Check if amounts are identical
                        amount1 = float(exp1.get("TotalAmt", 0))
                        amount2 = float(exp2.get("TotalAmt", 0))

                        if amount1 == amount2 and amount1 > 0:
                            # Check vendors
                            vendor1 = exp1.get("EntityRef", {}).get("name", "")
                            vendor2 = exp2.get("EntityRef", {}).get("name", "")

                            if vendor1 == vendor2:
                                # Check dates close (within 7 days)
                                date1 = datetime.strptime(
                                    exp1.get("TxnDate"), "%Y-%m-%d"
                                )
                                date2 = datetime.strptime(
                                    exp2.get("TxnDate"), "%Y-%m-%d"
                                )

                                if abs((date1 - date2).days) <= 7:
                                    potential_duplicates.append((exp1, exp2))

                if not potential_duplicates:
                    return [
                        TextContent(
                            type="text",
                            text="No potential duplicate transactions found for the specified period.",
                        )
                    ]

                # Format the duplicate information
                duplicate_text = f"Found {len(potential_duplicates)} potential duplicate transactions:\n\n"

                for idx, (exp1, exp2) in enumerate(potential_duplicates, 1):
                    vendor = exp1.get("EntityRef", {}).get("name", "Unknown Vendor")
                    amount = float(exp1.get("TotalAmt", 0))
                    date1 = exp1.get("TxnDate")
                    date2 = exp2.get("TxnDate")

                    duplicate_text += (
                        f"Duplicate #{idx}:\n"
                        f"  Vendor: {vendor}\n"
                        f"  Amount: ${amount:.2f}\n"
                        f"  First Transaction Date: {date1}\n"
                        f"  Second Transaction Date: {date2}\n"
                        f"  First Transaction ID: {exp1.get('Id')}\n"
                        f"  Second Transaction ID: {exp2.get('Id')}\n\n"
                    )

                return [TextContent(type="text", text=duplicate_text)]

            elif name == "analyze_customer_payment_patterns":
                customer_id = arguments.get("customer_id")
                lookback_months = arguments.get("lookback_months", 12)

                # Calculate lookback date
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30 * lookback_months)

                start_date_str = start_date.strftime("%Y-%m-%d")
                end_date_str = end_date.strftime("%Y-%m-%d")

                # Build query for invoices and payments
                if customer_id:
                    invoice_query = f"""
                    SELECT * FROM Invoice 
                    WHERE CustomerRef = '{customer_id}' AND
                    TxnDate >= '{start_date_str}' AND TxnDate <= '{end_date_str}'
                    MAXRESULTS 1000
                    """

                    payment_query = f"""
                    SELECT * FROM Payment 
                    WHERE CustomerRef = '{customer_id}' AND
                    TxnDate >= '{start_date_str}' AND TxnDate <= '{end_date_str}'
                    MAXRESULTS 1000
                    """

                    # Get customer info
                    customer_query = (
                        f"SELECT * FROM Customer WHERE Id = '{customer_id}'"
                    )
                    customer_result = await call_quickbooks_api(
                        "query",
                        credentials,
                        params={"query": customer_query},
                        user_id=server.user_id,
                        api_key=server.api_key,
                    )
                    customer = customer_result.get("QueryResponse", {}).get(
                        "Customer", [{}]
                    )[0]
                    customer_name = customer.get("DisplayName", "Unknown Customer")
                else:
                    invoice_query = f"""
                    SELECT * FROM Invoice 
                    WHERE TxnDate >= '{start_date_str}' AND TxnDate <= '{end_date_str}'
                    MAXRESULTS 1000
                    """

                    payment_query = f"""
                    SELECT * FROM Payment 
                    WHERE TxnDate >= '{start_date_str}' AND TxnDate <= '{end_date_str}'
                    MAXRESULTS 1000
                    """
                    customer_name = "All Customers"

                invoice_result = await call_quickbooks_api(
                    "query",
                    credentials,
                    params={"query": invoice_query},
                    user_id=server.user_id,
                    api_key=server.api_key,
                )
                payment_result = await call_quickbooks_api(
                    "query",
                    credentials,
                    params={"query": payment_query},
                    user_id=server.user_id,
                    api_key=server.api_key,
                )

                invoices = invoice_result.get("QueryResponse", {}).get("Invoice", [])
                payments = payment_result.get("QueryResponse", {}).get("Payment", [])

                # Analyze payment patterns
                total_invoices = len(invoices)
                total_payments = len(payments)

                if total_invoices == 0:
                    return [
                        TextContent(
                            type="text",
                            text=f"No invoices found for {customer_name} in the specified period.",
                        )
                    ]

                # Map payments to invoices
                payment_map = {}
                for payment in payments:
                    for line in payment.get("Line", []):
                        if "LinkedTxn" in line:
                            for linked_txn in line.get("LinkedTxn", []):
                                if linked_txn.get("TxnType") == "Invoice":
                                    invoice_id = linked_txn.get("TxnId")
                                    payment_date = payment.get("TxnDate")

                                    if invoice_id not in payment_map:
                                        payment_map[invoice_id] = payment_date

                # Calculate payment statistics
                total_days_to_pay = 0
                paid_invoices = 0
                unpaid_invoices = 0
                early_payments = 0  # Paid before due date
                on_time_payments = 0  # Paid on due date
                late_payments = 0  # Paid after due date

                for invoice in invoices:
                    invoice_id = invoice.get("Id")
                    invoice_date = datetime.strptime(invoice.get("TxnDate"), "%Y-%m-%d")
                    due_date = datetime.strptime(
                        invoice.get("DueDate", invoice.get("TxnDate")), "%Y-%m-%d"
                    )

                    if invoice_id in payment_map:
                        paid_invoices += 1
                        payment_date = datetime.strptime(
                            payment_map[invoice_id], "%Y-%m-%d"
                        )
                        days_to_pay = (payment_date - invoice_date).days
                        total_days_to_pay += days_to_pay

                        # Determine if payment was early, on-time, or late
                        if payment_date < due_date:
                            early_payments += 1
                        elif payment_date == due_date:
                            on_time_payments += 1
                        else:
                            late_payments += 1
                    else:
                        unpaid_invoices += 1

                # Calculate average days to pay
                avg_days_to_pay = (
                    total_days_to_pay / paid_invoices if paid_invoices > 0 else 0
                )
                payment_rate = (
                    (paid_invoices / total_invoices) * 100 if total_invoices > 0 else 0
                )

                # Format analysis results
                analysis_text = (
                    f"Payment Pattern Analysis for {customer_name}\n"
                    f"Period: {start_date_str} to {end_date_str}\n\n"
                    f"Total Invoices: {total_invoices}\n"
                    f"Paid Invoices: {paid_invoices} ({payment_rate:.1f}%)\n"
                    f"Unpaid Invoices: {unpaid_invoices}\n"
                    f"Average Days to Pay: {avg_days_to_pay:.1f} days\n\n"
                    f"Payment Timing:\n"
                    f"  Early Payments: {early_payments} ({early_payments/paid_invoices*100:.1f}% of paid invoices)\n"
                    f"  On-Time Payments: {on_time_payments} ({on_time_payments/paid_invoices*100:.1f}% of paid invoices)\n"
                    f"  Late Payments: {late_payments} ({late_payments/paid_invoices*100:.1f}% of paid invoices)\n"
                )

                return [TextContent(type="text", text=analysis_text)]

            elif name == "generate_financial_metrics":
                as_of_date = arguments.get(
                    "as_of_date", datetime.now().strftime("%Y-%m-%d")
                )
                include_trends = arguments.get("include_trends", True)

                # Get balance sheet data
                balance_sheet_query = """
                SELECT * FROM Account 
                MAXRESULTS 1000
                """

                # Get profit and loss data - current year
                current_year = datetime.strptime(as_of_date, "%Y-%m-%d").year
                start_of_year = f"{current_year}-01-01"

                profit_loss_query = f"""
                SELECT * FROM Invoice 
                WHERE TxnDate >= '{start_of_year}' AND TxnDate <= '{as_of_date}'
                MAXRESULTS 1000
                """

                expense_query = f"""
                SELECT * FROM Purchase 
                WHERE TxnDate >= '{start_of_year}' AND TxnDate <= '{as_of_date}'
                MAXRESULTS 1000
                """

                accounts_result = await call_quickbooks_api(
                    "query",
                    credentials,
                    params={"query": balance_sheet_query},
                    user_id=server.user_id,
                    api_key=server.api_key,
                )
                income_result = await call_quickbooks_api(
                    "query",
                    credentials,
                    params={"query": profit_loss_query},
                    user_id=server.user_id,
                    api_key=server.api_key,
                )
                expense_result = await call_quickbooks_api(
                    "query",
                    credentials,
                    params={"query": expense_query},
                    user_id=server.user_id,
                    api_key=server.api_key,
                )

                accounts = accounts_result.get("QueryResponse", {}).get("Account", [])
                invoices = income_result.get("QueryResponse", {}).get("Invoice", [])
                expenses = expense_result.get("QueryResponse", {}).get("Purchase", [])

                # Calculate key metrics

                # Balance Sheet items
                total_assets = sum(
                    float(account.get("CurrentBalance", 0))
                    for account in accounts
                    if account.get("Classification") == "Asset"
                )

                total_liabilities = sum(
                    float(account.get("CurrentBalance", 0))
                    for account in accounts
                    if account.get("Classification") == "Liability"
                )

                total_equity = sum(
                    float(account.get("CurrentBalance", 0))
                    for account in accounts
                    if account.get("Classification") == "Equity"
                )

                current_assets = sum(
                    float(account.get("CurrentBalance", 0))
                    for account in accounts
                    if account.get("Classification") == "Asset"
                    and account.get("AccountType")
                    in ["Bank", "Accounts Receivable", "Other Current Asset"]
                )

                current_liabilities = sum(
                    float(account.get("CurrentBalance", 0))
                    for account in accounts
                    if account.get("Classification") == "Liability"
                    and account.get("AccountType")
                    in ["Accounts Payable", "Credit Card", "Other Current Liability"]
                )

                # Income Statement items
                total_revenue = sum(
                    float(invoice.get("TotalAmt", 0)) for invoice in invoices
                )
                total_expenses = sum(
                    float(expense.get("TotalAmt", 0)) for expense in expenses
                )
                net_income = total_revenue - total_expenses

                # Calculate ratios
                current_ratio = (
                    current_assets / current_liabilities
                    if current_liabilities != 0
                    else "N/A"
                )
                debt_to_equity = (
                    total_liabilities / total_equity if total_equity != 0 else "N/A"
                )
                debt_to_assets = (
                    total_liabilities / total_assets if total_assets != 0 else "N/A"
                )
                profit_margin = (
                    (net_income / total_revenue) * 100 if total_revenue != 0 else "N/A"
                )
                return_on_assets = (
                    (net_income / total_assets) * 100 if total_assets != 0 else "N/A"
                )
                return_on_equity = (
                    (net_income / total_equity) * 100 if total_equity != 0 else "N/A"
                )

                # Format ratio values
                for ratio in [
                    current_ratio,
                    debt_to_equity,
                    debt_to_assets,
                    profit_margin,
                    return_on_assets,
                    return_on_equity,
                ]:
                    if ratio != "N/A":
                        ratio = f"{ratio:.2f}"

                # Format metrics
                metrics_text = (
                    f"Financial Metrics as of {as_of_date}\n\n"
                    f"Balance Sheet:\n"
                    f"  Total Assets: ${total_assets:.2f}\n"
                    f"  Total Liabilities: ${total_liabilities:.2f}\n"
                    f"  Total Equity: ${total_equity:.2f}\n\n"
                    f"Income Statement (YTD):\n"
                    f"  Total Revenue: ${total_revenue:.2f}\n"
                    f"  Total Expenses: ${total_expenses:.2f}\n"
                    f"  Net Income: ${net_income:.2f}\n\n"
                    f"Key Ratios:\n"
                    f"  Current Ratio: {current_ratio}\n"
                    f"  Debt-to-Equity: {debt_to_equity}\n"
                    f"  Debt-to-Assets: {debt_to_assets}\n"
                    f"  Profit Margin: {profit_margin}%\n"
                    f"  Return on Assets (ROA): {return_on_assets}%\n"
                    f"  Return on Equity (ROE): {return_on_equity}%\n"
                )

                return [TextContent(type="text", text=metrics_text)]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(f"Error calling QuickBooks tool {name}: {str(e)}")
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


# Main handler allows users to auth
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        # Run authentication flow
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
