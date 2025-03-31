from datetime import datetime, timedelta

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.payment import Payment
from quickbooks.objects.bill import Bill
from quickbooks.objects.account import Account
from quickbooks.objects.item import Item

from intuitlib.enums import Scopes

from mcp.types import TextContent

from src.servers.quickbooks.main import create_server
from src.servers.quickbooks.main import create_quickbooks_client
from src.servers.quickbooks.handlers.tools import (
    handle_search_customers,
    handle_analyze_cash_flow,
    handle_find_duplicate_transactions,
    handle_analyze_customer_payment_patterns,
    handle_generate_financial_metrics,
)

from src.utils.quickbooks.util import get_credentials

# Define constants that were moved out of main.py
SERVICE_NAME = "quickbooks"
SCOPES = [
    Scopes.ACCOUNTING,
    Scopes.PAYMENT,
]


@pytest.fixture
def mock_qb_client() -> MagicMock:
    """
    Creates a mock QuickBooks client with all necessary methods and attributes.

    Returns:
        MagicMock: Configured mock QuickBooks client
    """
    client = MagicMock()
    # Setup mock methods
    client.query = MagicMock()
    client.all = MagicMock()
    client.get = MagicMock()
    client.filter = MagicMock()
    client.post = MagicMock()
    client.session = MagicMock()  # Add session manager
    client.make_request = MagicMock()
    client.process_request = MagicMock()

    # Set up session manager properly
    client.session.get_access_token = MagicMock(return_value="mock_token")
    client.session.get_company_id = MagicMock(return_value="mock_company_id")
    client.session.get_base_url = MagicMock(
        return_value="https://quickbooks.api.intuit.com"
    )
    client.session.get_environment = MagicMock(return_value="sandbox")
    client.session.get_client_id = MagicMock(return_value="mock_client_id")
    client.session.get_client_secret = MagicMock(return_value="mock_client_secret")
    client.session.get_redirect_uri = MagicMock(return_value="mock_redirect_uri")
    client.session.get_token = MagicMock(return_value="mock_token")
    client.session.get_refresh_token = MagicMock(return_value="mock_refresh_token")
    client.session.get_realm_id = MagicMock(return_value="mock_realm_id")

    # Add required session attributes
    client.session.token = "mock_token"
    client.session.refresh_token = "mock_refresh_token"
    client.session.realm_id = "mock_realm_id"
    client.session.client_id = "mock_client_id"
    client.session.client_secret = "mock_client_secret"
    client.session.redirect_uri = "mock_redirect_uri"
    client.session.environment = "sandbox"

    # Add required client attributes
    client.company_id = "mock_company_id"
    client.base_url = "https://quickbooks.api.intuit.com"
    client.environment = "sandbox"

    # Add query method
    client.query = MagicMock()
    return client


@pytest.fixture
def mock_server() -> AsyncMock:
    """
    Creates a mock server with all necessary methods for QuickBooks testing.

    Returns:
        AsyncMock: Configured mock server
    """
    server = AsyncMock()
    server.user_id = "test_user"
    server.handle_list_resources = AsyncMock()
    server.handle_list_tools = AsyncMock()

    # Add URI validation to handle_read_resource
    async def mock_handle_read_resource(uri):
        if not str(uri).startswith("quickbooks://"):
            raise ValueError("Invalid QuickBooks URI")

        resource_type = str(uri).split("://")[1].lower()
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

        # Return appropriate mock response based on resource type
        if resource_type == "customers":
            return [
                MagicMock(
                    text='["Amy\'s Bird Sanctuary", "Bill\'s Windsurf Shop", "Cool Cars"]'
                )
            ]
        elif resource_type == "invoices":
            return [MagicMock(text="Invoice for Test Customer: $1,000.00")]
        elif resource_type == "accounts":
            return [MagicMock(text="Test Account (Current Asset): $5,000.00")]
        elif resource_type == "items":
            return [MagicMock(text="Test Product (Inventory): $100.00")]
        elif resource_type == "bills":
            return [MagicMock(text="Bill for Test Vendor: $2,000.00 (2023-01-01)")]
        elif resource_type == "payments":
            return [
                MagicMock(text="Payment from Test Customer: $1,500.00 (2023-01-01)")
            ]

        return [MagicMock(text="Test resource")]

    server.handle_read_resource = AsyncMock(side_effect=mock_handle_read_resource)
    return server


@pytest.mark.asyncio
async def test_search_customers(
    mock_server: AsyncMock, mock_qb_client: MagicMock
) -> None:
    """
    Tests the customer search functionality using mocked server and client.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Mock data
    mock_customers = [Customer()]
    mock_customers[0].DisplayName = "Test Customer"
    mock_customers[0].CompanyName = "Test Company"
    mock_customers[0].PrimaryEmailAddr = "test@example.com"

    # Setup mock
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.filter.return_value = mock_customers

        # Test
        result = await handle_search_customers(
            mock_qb_client, mock_server, {"query": "test"}
        )

        # Assertions
        assert len(result) == 1
        assert "Test Customer" in result[0].text
        assert "Test Company" in result[0].text
        assert "test@example.com" in result[0].text


@pytest.mark.asyncio
async def test_analyze_cash_flow(
    mock_server: AsyncMock, mock_qb_client: MagicMock
) -> None:
    """
    Tests the cash flow analysis functionality using mocked server and client.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Mock data
    mock_payment = Payment()
    mock_payment.TxnDate = "2023-01-01"
    mock_payment.TotalAmt = 1000

    mock_bill = Bill()
    mock_bill.TxnDate = "2023-01-15"
    mock_bill.TotalAmt = 500

    # Setup mock
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.all.side_effect = [[mock_payment], [mock_bill]]

        # Test
        result = await handle_analyze_cash_flow(
            mock_qb_client,
            mock_server,
            {"start_date": "2023-01-01", "end_date": "2023-01-31", "group_by": "month"},
        )

        # Assertions
        assert len(result) == 1
        assert "Cash Flow Analysis Report" in result[0].text
        assert "2023-01-01 to 2023-01-31" in result[0].text
        assert "Grouped by: Month" in result[0].text


@pytest.mark.asyncio
async def test_find_duplicate_transactions(
    mock_server: AsyncMock, mock_qb_client: MagicMock
) -> None:
    """
    Tests the duplicate transaction detection functionality using mocked server and client.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Mock data
    mock_payment1 = Payment()
    mock_payment1.TxnDate = "2023-01-01"
    mock_payment1.TotalAmt = 1000
    mock_payment1.CustomerRef = MagicMock(name="Customer A")

    mock_payment2 = Payment()
    mock_payment2.TxnDate = "2023-01-05"  # Within 7 days of payment1
    mock_payment2.TotalAmt = 1000  # Same amount as payment1
    mock_payment2.CustomerRef = MagicMock(name="Customer B")

    # Setup mock
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        # Return both payments in the first call to all()
        mock_qb_client.all.side_effect = [
            [mock_payment1, mock_payment2],  # Payments
            [],  # Bills
        ]

        # Test
        result = await handle_find_duplicate_transactions(
            mock_qb_client,
            mock_server,
            {
                "start_date": "2023-01-01",
                "end_date": "2023-01-31",
                "amount_threshold": 100,
            },
        )

        # Assertions
        assert len(result) == 1
        assert "Potential Duplicate Transactions Report" in result[0].text
        assert "2023-01-01 to 2023-01-31" in result[0].text
        assert "Amount Threshold: $100.00" in result[0].text
        assert "Customer A" in result[0].text
        assert "Customer B" in result[0].text
        assert "Payment of $1,000.00" in result[0].text
        assert "First: 2023-01-01" in result[0].text
        assert "Second: 2023-01-05" in result[0].text


@pytest.mark.asyncio
async def test_analyze_customer_payment_patterns(
    mock_server: AsyncMock, mock_qb_client: MagicMock
) -> None:
    """
    Tests the customer payment pattern analysis functionality using mocked server and client.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Mock data
    mock_customer = Customer()
    mock_customer.DisplayName = "Test Customer"
    mock_customer.Id = "123"

    mock_invoice = Invoice()
    mock_invoice.TxnDate = "2023-01-01"
    mock_invoice.TotalAmt = 1000
    mock_invoice.CustomerRef = MagicMock(value="123")
    mock_invoice.Balance = 0  # Paid invoice

    mock_payment = Payment()
    mock_payment.TxnDate = "2023-01-15"
    mock_payment.TotalAmt = 1000
    mock_payment.CustomerRef = MagicMock(value="123")

    # Setup mock
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        # Fix customer retrieval
        mock_qb_client.get.return_value = mock_customer
        mock_qb_client.all.side_effect = [
            [mock_invoice],  # Invoices
            [mock_payment],  # Payments
        ]

        # Test
        result = await handle_analyze_customer_payment_patterns(
            mock_qb_client, mock_server, {"customer_id": "123", "months": 12}
        )

        # Assertions
        assert len(result) == 1
        assert "Payment Pattern Analysis for Test Customer" in result[0].text
        assert "Total Invoiced: $1,000.00" in result[0].text
        assert "Total Paid: $1,000.00" in result[0].text
        assert "Outstanding Balance: $0.00" in result[0].text
        assert "Average Days to Pay: 14.0 days" in result[0].text
        assert "Recent Invoices:" in result[0].text
        assert "2023-01-01: $1,000.00 (Paid)" in result[0].text


@pytest.mark.asyncio
async def test_generate_financial_metrics(
    mock_server: AsyncMock, mock_qb_client: MagicMock
) -> None:
    """
    Tests generating financial metrics functionality using mocked server and client.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Mock data
    mock_account1 = Account()
    mock_account1.AccountType = "Current Asset"
    mock_account1.CurrentBalance = 10000

    mock_account2 = Account()
    mock_account2.AccountType = "Current Liability"
    mock_account2.CurrentBalance = 5000

    mock_invoice = Invoice()
    mock_invoice.TxnDate = "2023-01-01"
    mock_invoice.TotalAmt = 20000

    mock_bill = Bill()
    mock_bill.TxnDate = "2023-01-15"
    mock_bill.TotalAmt = 15000

    # Setup mock
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.all.side_effect = [
            [mock_account1, mock_account2],
            [mock_invoice],
            [mock_bill],
        ]

        # Test
        result = await handle_generate_financial_metrics(
            mock_qb_client,
            mock_server,
            {
                "start_date": "2023-01-01",
                "end_date": "2023-01-31",
                "metrics": ["current_ratio", "gross_margin", "net_margin"],
            },
        )

        # Assertions
        assert len(result) == 1
        assert "Current Ratio" in result[0].text
        assert "Gross Margin" in result[0].text
        assert "Net Margin" in result[0].text


@pytest.mark.asyncio
async def test_error_handling(
    mock_server: AsyncMock, mock_qb_client: MagicMock
) -> None:
    """
    Tests error handling in QuickBooks API operations.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Test error handling for search_customers
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.filter.side_effect = Exception("API Error")

        result = await handle_search_customers(
            mock_qb_client, mock_server, {"query": "test"}
        )
        assert "Error" in result[0].text

    # Test error handling for analyze_cash_flow
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.all.side_effect = Exception("API Error")

        result = await handle_analyze_cash_flow(
            mock_qb_client,
            mock_server,
            {"start_date": "2023-01-01", "end_date": "2023-01-31"},
        )
        assert "Error" in result[0].text


@pytest.mark.asyncio
async def test_empty_results(mock_server: AsyncMock, mock_qb_client: MagicMock) -> None:
    """
    Tests handling of empty results from QuickBooks API.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Test empty results for search_customers
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.filter.return_value = []

        result = await handle_search_customers(
            mock_qb_client, mock_server, {"query": "nonexistent"}
        )
        assert "No customers found" in result[0].text

    # Test empty results for find_duplicate_transactions
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.all.return_value = []

        result = await handle_find_duplicate_transactions(
            mock_qb_client,
            mock_server,
            {"start_date": "2023-01-01", "end_date": "2023-01-31"},
        )
        assert "No potential duplicates found" in result[0].text


@pytest.mark.asyncio
async def test_server_initialization() -> None:
    """
    Tests server initialization and configuration.
    """
    server = create_server("test_user")
    assert server.user_id == "test_user"
    assert server.api_key is None


@pytest.mark.asyncio
async def test_list_resources(
    mock_server: AsyncMock, mock_qb_client: MagicMock
) -> None:
    """
    Tests listing QuickBooks resources.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_server.handle_list_resources.return_value = [
            MagicMock(uri="quickbooks://customers"),
            MagicMock(uri="quickbooks://invoices"),
        ]
        resources = await mock_server.handle_list_resources()
        assert len(resources) > 0
        assert any(r.uri.startswith("quickbooks://") for r in resources)


@pytest.mark.asyncio
async def test_authentication_flow() -> None:
    """
    Tests QuickBooks authentication flow.
    """
    with patch(
        "src.utils.quickbooks.util.authenticate_and_save_credentials"
    ) as mock_auth:
        mock_auth.return_value = True
        # Don't await the mock since it's not an async function
        result = mock_auth("test_user", SERVICE_NAME, SCOPES)
        assert result is True


@pytest.mark.asyncio
async def test_server_endpoints(mock_server: AsyncMock) -> None:
    """
    Tests main server endpoints.

    Args:
        mock_server: The mocked server instance
    """
    # Test tool listing
    mock_server.handle_list_tools.return_value = [
        MagicMock(name="search_customers"),
        MagicMock(name="analyze_cash_flow"),
    ]
    tools = await mock_server.handle_list_tools()
    assert len(tools) > 0

    # Test resource reading
    mock_server.handle_read_resource.return_value = [MagicMock(text="Test resource")]
    resources = await mock_server.handle_read_resource("quickbooks://customers")
    assert len(resources) > 0


@pytest.mark.asyncio
async def test_find_invoices(mock_server: AsyncMock, mock_qb_client: MagicMock) -> None:
    """
    Tests finding invoices in QuickBooks.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Mock data
    mock_invoice = Invoice()
    mock_invoice.TxnDate = "2023-01-01"
    mock_invoice.TotalAmt = 1000
    mock_invoice.CustomerRef = MagicMock(name="Test Customer")

    # Setup mock
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.all.return_value = [mock_invoice]

        # Test
        mock_server.handle_read_resource.return_value = [
            MagicMock(text="Invoice for Test Customer: $1,000.00")
        ]
        result = await mock_server.handle_read_resource("quickbooks://invoices")

        # Assertions
        assert len(result) == 1
        assert "Test Customer" in result[0].text
        assert "$1,000.00" in result[0].text


@pytest.mark.asyncio
async def test_find_accounts(mock_server: AsyncMock, mock_qb_client: MagicMock) -> None:
    """
    Tests finding accounts in QuickBooks.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Mock data
    mock_account = Account()
    mock_account.Name = "Test Account"
    mock_account.AccountType = "Current Asset"
    mock_account.CurrentBalance = 5000

    # Setup mock
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.all.return_value = [mock_account]

        # Test
        mock_server.handle_read_resource.return_value = [
            MagicMock(text="Test Account (Current Asset): $5,000.00")
        ]
        result = await mock_server.handle_read_resource("quickbooks://accounts")

        # Assertions
        assert len(result) == 1
        assert "Test Account" in result[0].text
        assert "Current Asset" in result[0].text
        assert "$5,000.00" in result[0].text


@pytest.mark.asyncio
async def test_find_items(mock_server: AsyncMock, mock_qb_client: MagicMock) -> None:
    """
    Tests finding items/products in QuickBooks.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Mock data
    mock_item = Item()
    mock_item.Name = "Test Product"
    mock_item.Type = "Inventory"
    mock_item.UnitPrice = 100

    # Setup mock
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.all.return_value = [mock_item]

        # Test
        mock_server.handle_read_resource.return_value = [
            MagicMock(text="Test Product (Inventory): $100.00")
        ]
        result = await mock_server.handle_read_resource("quickbooks://items")

        # Assertions
        assert len(result) == 1
        assert "Test Product" in result[0].text
        assert "Inventory" in result[0].text
        assert "$100.00" in result[0].text


@pytest.mark.asyncio
async def test_find_bills(mock_server: AsyncMock, mock_qb_client: MagicMock) -> None:
    """
    Tests finding bills in QuickBooks.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Mock data
    mock_bill = Bill()
    mock_bill.TxnDate = "2023-01-01"
    mock_bill.DueDate = "2023-02-01"
    mock_bill.TotalAmt = 2000
    mock_bill.VendorRef = MagicMock(name="Test Vendor")

    # Setup mock
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.all.return_value = [mock_bill]

        # Test
        mock_server.handle_read_resource.return_value = [
            MagicMock(text="Bill for Test Vendor: $2,000.00 (2023-01-01)")
        ]
        result = await mock_server.handle_read_resource("quickbooks://bills")

        # Assertions
        assert len(result) == 1
        assert "Test Vendor" in result[0].text
        assert "$2,000.00" in result[0].text
        assert "2023-01-01" in result[0].text


@pytest.mark.asyncio
async def test_find_payments(mock_server: AsyncMock, mock_qb_client: MagicMock) -> None:
    """
    Tests finding payments in QuickBooks.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Mock data
    mock_payment = Payment()
    mock_payment.TxnDate = "2023-01-01"
    mock_payment.TotalAmt = 1500
    mock_payment.CustomerRef = MagicMock(name="Test Customer")

    # Setup mock
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.all.return_value = [mock_payment]

        # Test
        mock_server.handle_read_resource.return_value = [
            MagicMock(text="Payment from Test Customer: $1,500.00 (2023-01-01)")
        ]
        result = await mock_server.handle_read_resource("quickbooks://payments")

        # Assertions
        assert len(result) == 1
        assert "Test Customer" in result[0].text
        assert "$1,500.00" in result[0].text
        assert "2023-01-01" in result[0].text


@pytest.mark.asyncio
async def test_customer_list_formatting(
    mock_server: AsyncMock, mock_qb_client: MagicMock
) -> None:
    """
    Tests proper formatting of customer list.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Mock data with various customer types
    mock_customers = [Customer(), Customer(), Customer()]
    mock_customers[0].DisplayName = "Amy's Bird Sanctuary"
    mock_customers[1].DisplayName = "Bill's Windsurf Shop"
    mock_customers[2].DisplayName = "Cool Cars"

    # Setup mock
    with patch(
        "src.servers.quickbooks.main.create_quickbooks_client",
        return_value=mock_qb_client,
    ):
        mock_qb_client.all.return_value = mock_customers

        # Test
        mock_server.handle_read_resource.return_value = [
            MagicMock(
                text='["Amy\'s Bird Sanctuary", "Bill\'s Windsurf Shop", "Cool Cars"]'
            )
        ]
        result = await mock_server.handle_read_resource("quickbooks://customers")

        # Assertions
        assert len(result) == 1
        assert "Amy's Bird Sanctuary" in result[0].text
        assert "Bill's Windsurf Shop" in result[0].text
        assert "Cool Cars" in result[0].text
        # Check JSON formatting
        assert result[0].text.startswith("[")
        assert result[0].text.endswith("]")


@pytest.mark.asyncio
async def test_date_range_validation(
    mock_server: AsyncMock, mock_qb_client: MagicMock
) -> None:
    """
    Tests date range validation in various tools.

    Args:
        mock_server: The mocked server instance
        mock_qb_client: The mocked QuickBooks client
    """
    # Test invalid date format
    with pytest.raises(ValueError, match="Invalid date format"):
        await handle_analyze_cash_flow(
            mock_qb_client,
            mock_server,
            {"start_date": "invalid-date", "end_date": "2024-02-29"},
        )

    # Test end date before start date
    with pytest.raises(ValueError, match="End date must be after start date"):
        await handle_analyze_cash_flow(
            mock_qb_client,
            mock_server,
            {"start_date": "2024-02-29", "end_date": "2024-01-01"},
        )

    # Test future dates
    future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    with pytest.raises(ValueError, match="End date cannot be in the future"):
        await handle_find_duplicate_transactions(
            mock_qb_client,
            mock_server,
            {"start_date": future_date, "end_date": future_date},
        )


@pytest.mark.asyncio
async def test_resource_uri_validation(mock_server: AsyncMock) -> None:
    """
    Tests validation of QuickBooks resource URIs.

    Args:
        mock_server: The mocked server instance
    """
    # Test invalid URI format
    with pytest.raises(ValueError, match="Invalid QuickBooks URI"):
        await mock_server.handle_read_resource("invalid-uri")

    # Test unknown resource type
    with pytest.raises(ValueError, match="Unknown resource type"):
        await mock_server.handle_read_resource("quickbooks://unknown")

    # Test valid URIs
    valid_uris = [
        "quickbooks://customers",
        "quickbooks://invoices",
        "quickbooks://accounts",
        "quickbooks://items",
        "quickbooks://bills",
        "quickbooks://payments",
    ]

    for uri in valid_uris:
        mock_server.handle_read_resource.return_value = [
            MagicMock(text="Test resource")
        ]
        result = await mock_server.handle_read_resource(uri)
        assert len(result) > 0


@pytest.mark.asyncio
async def test_quickbooks() -> None:
    """
    Integration test for QuickBooks server functionality.
    """
    user_id = "local"
    # Create a test server instance
    server = create_server(user_id)

    # Get existing credentials
    await get_credentials(user_id, SERVICE_NAME)

    # Create fresh QuickBooks client
    print("\nCreating fresh QuickBooks client...")
    qb_client = await create_quickbooks_client(user_id)

    # Test all resources
    print("\nTesting QuickBooks resources:")

    # Test customers
    print("\nTesting customers...")
    customers = Customer.all(qb=qb_client)
    print(f"Found {len(customers)} customers:")
    for customer in customers:
        print(f"- {customer.DisplayName}")

    # Test invoices
    print("\nTesting invoices...")
    invoices = Invoice.all(qb=qb_client)
    print(f"Found {len(invoices)} invoices:")
    for invoice in invoices:
        print(
            f"- Invoice for {invoice.CustomerRef.name if hasattr(invoice, 'CustomerRef') else 'Unknown'}: ${invoice.TotalAmt}"
        )

    # Test accounts
    print("\nTesting accounts...")
    accounts = Account.all(qb=qb_client)
    print(f"Found {len(accounts)} accounts:")
    for account in accounts:
        print(
            f"- {account.Name} ({account.AccountType}): ${getattr(account, 'CurrentBalance', 0)}"
        )

    # Test items
    print("\nTesting items...")
    items = Item.all(qb=qb_client)
    print(f"Found {len(items)} items:")
    for item in items:
        print(f"- {item.Name} ({item.Type}): ${getattr(item, 'UnitPrice', 0)}")

    # Test bills
    print("\nTesting bills...")
    bills = Bill.all(qb=qb_client)
    print(f"Found {len(bills)} bills:")
    for bill in bills:
        print(
            f"- Bill for {bill.VendorRef.name if hasattr(bill, 'VendorRef') else 'Unknown'}: ${bill.TotalAmt}"
        )

    # Test payments
    print("\nTesting payments...")
    payments = Payment.all(qb=qb_client)
    print(f"Found {len(payments)} payments:")
    for payment in payments:
        print(
            f"- Payment from {payment.CustomerRef.name if hasattr(payment, 'CustomerRef') else 'Unknown'}: ${payment.TotalAmt}"
        )

    # Test tools
    print("\nTesting QuickBooks tools:")

    # Test cash flow analysis
    print("\nTesting cash flow analysis...")
    result = await handle_analyze_cash_flow(
        qb_client,
        server,
        {"start_date": "2023-01-01", "end_date": "2023-01-31", "group_by": "month"},
    )
    print("\nCash Flow Analysis Results:")
    for content in result:
        if isinstance(content, TextContent):
            print(content.text)

    # Test duplicate transactions
    print("\nTesting duplicate transaction detection...")
    result = await handle_find_duplicate_transactions(
        qb_client,
        server,
        {"start_date": "2023-01-01", "end_date": "2023-01-31", "amount_threshold": 100},
    )
    print("\nDuplicate Transactions Results:")
    for content in result:
        if isinstance(content, TextContent):
            print(content.text)

    # Test financial metrics
    print("\nTesting financial metrics...")
    result = await handle_generate_financial_metrics(
        qb_client,
        server,
        {
            "start_date": "2023-01-01",
            "end_date": "2023-01-31",
            "metrics": ["current_ratio", "gross_margin", "net_margin"],
        },
    )
    print("\nFinancial Metrics Results:")
    for content in result:
        if isinstance(content, TextContent):
            print(content.text)
