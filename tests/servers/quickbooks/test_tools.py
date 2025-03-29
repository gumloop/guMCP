import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.payment import Payment
from quickbooks.objects.bill import Bill
from quickbooks.objects.account import Account
from quickbooks.objects.journalentry import JournalEntry

from ....src.servers.quickbooks.handlers.tools import (
    handle_search_customers,
    handle_analyze_sred,
    handle_analyze_cash_flow,
    handle_find_duplicate_transactions,
    handle_analyze_customer_payment_patterns,
    handle_generate_financial_metrics,
)

@pytest.fixture
def mock_qb_client():
    client = AsyncMock()
    return client

@pytest.fixture
def mock_server():
    server = MagicMock()
    server.user_id = "test_user"
    return server

@pytest.mark.asyncio
async def test_search_customers(mock_server, mock_qb_client):
    # Mock data
    mock_customers = [
        Customer()
    ]
    mock_customers[0].DisplayName = "Test Customer"
    mock_customers[0].CompanyName = "Test Company"
    mock_customers[0].PrimaryEmailAddr = "test@example.com"
    
    # Setup mock
    with patch("src.servers.quickbooks.handlers.tools.create_quickbooks_client", return_value=mock_qb_client):
        mock_qb_client.filter.return_value = mock_customers
        
        # Test
        result = await handle_search_customers(mock_server, {"query": "test"})
        
        # Assertions
        assert len(result) == 1
        assert "Test Customer" in result[0].text
        assert "Test Company" in result[0].text
        assert "test@example.com" in result[0].text

@pytest.mark.asyncio
async def test_analyze_sred(mock_server, mock_qb_client):
    # Mock data
    mock_journal_entry = JournalEntry()
    mock_journal_entry.TxnDate = "2023-01-01"
    mock_journal_entry.Line = [
        MagicMock(Description="Research and development", Amount=1000)
    ]
    
    mock_bill = Bill()
    mock_bill.TxnDate = "2023-01-02"
    mock_bill.Description = "Engineering services"
    mock_bill.TotalAmt = 2000
    
    # Setup mock
    with patch("src.servers.quickbooks.handlers.tools.create_quickbooks_client", return_value=mock_qb_client):
        mock_qb_client.query.side_effect = [
            [mock_journal_entry],
            [mock_bill]
        ]
        
        # Test
        result = await handle_analyze_sred(mock_server, {
            "start_date": "2023-01-01",
            "end_date": "2023-01-31"
        })
        
        # Assertions
        assert len(result) == 1
        assert "Research and development" in result[0].text
        assert "Engineering services" in result[0].text
        assert "$3,000.00" in result[0].text

@pytest.mark.asyncio
async def test_analyze_cash_flow(mock_server, mock_qb_client):
    # Mock data
    mock_payment = Payment()
    mock_payment.TxnDate = "2023-01-01"
    mock_payment.TotalAmt = 1000
    
    mock_bill = Bill()
    mock_bill.TxnDate = "2023-01-15"
    mock_bill.TotalAmt = 500
    
    # Setup mock
    with patch("src.servers.quickbooks.handlers.tools.create_quickbooks_client", return_value=mock_qb_client):
        mock_qb_client.all.side_effect = [
            [mock_payment],
            [mock_bill]
        ]
        
        # Test
        result = await handle_analyze_cash_flow(mock_server, {
            "start_date": "2023-01-01",
            "end_date": "2023-01-31"
        })
        
        # Assertions
        assert len(result) == 1
        assert "$1,000.00" in result[0].text  # Inflow
        assert "$500.00" in result[0].text    # Outflow
        assert "$500.00" in result[0].text    # Net cash flow

@pytest.mark.asyncio
async def test_find_duplicate_transactions(mock_server, mock_qb_client):
    # Mock data
    mock_payment1 = Payment()
    mock_payment1.TxnDate = "2023-01-01"
    mock_payment1.TotalAmt = 1000
    mock_payment1.CustomerRef = MagicMock(name="Customer A")
    
    mock_payment2 = Payment()
    mock_payment2.TxnDate = "2023-01-05"
    mock_payment2.TotalAmt = 1000
    mock_payment2.CustomerRef = MagicMock(name="Customer B")
    
    # Setup mock
    with patch("src.servers.quickbooks.handlers.tools.create_quickbooks_client", return_value=mock_qb_client):
        mock_qb_client.all.side_effect = [
            [mock_payment1, mock_payment2],
            []
        ]
        
        # Test
        result = await handle_find_duplicate_transactions(mock_server, {
            "start_date": "2023-01-01",
            "end_date": "2023-01-31"
        })
        
        # Assertions
        assert len(result) == 1
        assert "Payment" in result[0].text
        assert "$1,000.00" in result[0].text
        assert "Customer A" in result[0].text
        assert "Customer B" in result[0].text

@pytest.mark.asyncio
async def test_analyze_customer_payment_patterns(mock_server, mock_qb_client):
    # Mock data
    mock_customer = Customer()
    mock_customer.DisplayName = "Test Customer"
    
    mock_invoice = Invoice()
    mock_invoice.TxnDate = "2023-01-01"
    mock_invoice.TotalAmt = 1000
    mock_invoice.CustomerRef = MagicMock(value="123")
    
    mock_payment = Payment()
    mock_payment.TxnDate = "2023-01-15"
    mock_payment.TotalAmt = 1000
    mock_payment.CustomerRef = MagicMock(value="123")
    
    # Setup mock
    with patch("src.servers.quickbooks.handlers.tools.create_quickbooks_client", return_value=mock_qb_client):
        mock_qb_client.get.return_value = mock_customer
        mock_qb_client.all.side_effect = [
            [mock_invoice],
            [mock_payment]
        ]
        
        # Test
        result = await handle_analyze_customer_payment_patterns(mock_server, {
            "customer_id": "123"
        })
        
        # Assertions
        assert len(result) == 1
        assert "Test Customer" in result[0].text
        assert "$1,000.00" in result[0].text
        assert "Paid" in result[0].text

@pytest.mark.asyncio
async def test_generate_financial_metrics(mock_server, mock_qb_client):
    # Mock data
    mock_account1 = Account()
    mock_account1.AccountType = "Current Asset"
    mock_account1.Balance = 1000
    
    mock_account2 = Account()
    mock_account2.AccountType = "Current Liability"
    mock_account2.Balance = 500
    
    mock_invoice = Invoice()
    mock_invoice.TxnDate = "2023-01-01"
    mock_invoice.TotalAmt = 2000
    
    mock_bill = Bill()
    mock_bill.TxnDate = "2023-01-15"
    mock_bill.TotalAmt = 1000
    mock_bill.AccountRef = MagicMock(name="Operating Expenses")
    
    # Setup mock
    with patch("src.servers.quickbooks.handlers.tools.create_quickbooks_client", return_value=mock_qb_client):
        mock_qb_client.all.side_effect = [
            [mock_account1, mock_account2],
            [mock_invoice],
            [mock_bill]
        ]
        
        # Test
        result = await handle_generate_financial_metrics(mock_server, {
            "start_date": "2023-01-01",
            "end_date": "2023-01-31",
            "metrics": ["current_ratio", "gross_margin", "net_margin"]
        })
        
        # Assertions
        assert len(result) == 1
        assert "Current Ratio" in result[0].text
        assert "Gross Margin" in result[0].text
        assert "Net Margin" in result[0].text

@pytest.mark.asyncio
async def test_error_handling(mock_server, mock_qb_client):
    # Test error handling for search_customers
    with patch("src.servers.quickbooks.handlers.tools.create_quickbooks_client", return_value=mock_qb_client):
        mock_qb_client.filter.side_effect = Exception("API Error")
        
        result = await handle_search_customers(mock_server, {"query": "test"})
        assert "Error" in result[0].text
    
    # Test error handling for analyze_sred
    with patch("src.servers.quickbooks.handlers.tools.create_quickbooks_client", return_value=mock_qb_client):
        mock_qb_client.query.side_effect = Exception("API Error")
        
        result = await handle_analyze_sred(mock_server, {
            "start_date": "2023-01-01",
            "end_date": "2023-01-31"
        })
        assert "Error" in result[0].text

@pytest.mark.asyncio
async def test_empty_results(mock_server, mock_qb_client):
    # Test empty results for search_customers
    with patch("src.servers.quickbooks.handlers.tools.create_quickbooks_client", return_value=mock_qb_client):
        mock_qb_client.filter.return_value = []
        
        result = await handle_search_customers(mock_server, {"query": "nonexistent"})
        assert "No customers found" in result[0].text
    
    # Test empty results for find_duplicate_transactions
    with patch("src.servers.quickbooks.handlers.tools.create_quickbooks_client", return_value=mock_qb_client):
        mock_qb_client.all.return_value = []
        
        result = await handle_find_duplicate_transactions(mock_server, {
            "start_date": "2023-01-01",
            "end_date": "2023-01-31"
        })
        assert "No potential duplicates found" in result[0].text 