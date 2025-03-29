import json
import logging
from datetime import datetime, timedelta
from typing import List
import requests
from mcp.types import TextContent
from quickbooks.objects.customer import Customer
from quickbooks.objects.journalentry import JournalEntry
from quickbooks.objects.bill import Bill
from quickbooks.objects.account import Account
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.payment import Payment

from ..utils.client import create_quickbooks_client
from ..utils.formatters import format_customer, format_invoice, format_account

logger = logging.getLogger(__name__)

async def handle_search_customers(server, arguments):
    """Handle customer search tool"""
    if "query" not in arguments:
        raise ValueError("Missing query parameter")

    query = arguments["query"]
    limit = arguments.get("limit", 10)

    qb_client = await create_quickbooks_client(server.user_id)
    customers = Customer.filter(qb_client, 
                              f"DisplayName LIKE '%{query}%' OR "
                              f"CompanyName LIKE '%{query}%' OR "
                              f"PrimaryEmailAddr LIKE '%{query}%'", 
                              max_results=limit)
    
    formatted_customers = [format_customer(c) for c in customers]
    
    if not formatted_customers:
        return [TextContent(type="text", text="No customers found matching your query.")]
    
    result_text = json.dumps(formatted_customers, indent=2)
    return [TextContent(type="text", text=f"Found {len(formatted_customers)} customers:\n\n{result_text}")]

async def handle_analyze_sred(server, arguments):
    """Handle SR&ED analysis tool with improved categorization and analysis"""
    logger.debug("Starting SR&ED analysis with arguments: %s", arguments)
    
    if not all(k in arguments for k in ["start_date", "end_date"]):
        raise ValueError("Missing required parameters: start_date, end_date")

    start_date = arguments["start_date"]
    end_date = arguments["end_date"]
    
    # Define SR&ED categories and their associated keywords
    sred_categories = {
        "Technological Advancement": [
            "new technology", "innovation", "advancement", "novel", "breakthrough",
            "state of the art", "cutting edge", "pioneering"
        ],
        "Technical Uncertainty": [
            "uncertainty", "challenge", "obstacle", "unknown", "technical risk",
            "feasibility", "investigation", "problem solving"
        ],
        "Systematic Investigation": [
            "experiment", "testing", "prototype", "methodology", "analysis",
            "research", "development", "trial", "iteration", "validation"
        ],
        "Technical Content": [
            "engineering", "scientific", "technical", "software development",
            "algorithm", "design", "architecture", "implementation"
        ]
    }
    
    # Add user-provided keywords to appropriate categories
    if "keywords" in arguments:
        for keyword in arguments["keywords"]:
            # Add to Technical Content by default
            sred_categories["Technical Content"].append(keyword)

    try:
        qb_client = await create_quickbooks_client(server.user_id)
        
        # Get journal entries
        journal_entries = JournalEntry.query(
            f"SELECT * FROM JournalEntry WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' ORDER BY TxnDate",
            qb_client
        )
        
        # Get bills
        bills = Bill.query(
            f"SELECT * FROM Bill WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' ORDER BY TxnDate",
            qb_client
        )
        
        def calculate_confidence_score(description, category_keywords):
            """Calculate confidence score based on keyword matches and context"""
            if not description:
                return 0
            
            description = description.lower()
            score = 0
            matches = 0
            
            for keyword in category_keywords:
                if keyword.lower() in description:
                    matches += 1
                    # Give higher score for multi-word matches
                    score += 2 if " " in keyword else 1
            
            # Normalize score between 0 and 1
            max_possible_score = 2 * len(category_keywords)
            return min(score / max_possible_score, 1.0)

        def analyze_transaction(trans_type, date, description, amount, extra_info=None):
            """Analyze a single transaction for SR&ED relevance"""
            results = []
            
            for category, keywords in sred_categories.items():
                confidence = calculate_confidence_score(description, keywords)
                if confidence > 0.1:  # Only include if there's at least some relevance
                    result = {
                        "type": trans_type,
                        "date": date,
                        "description": description,
                        "amount": amount,
                        "category": category,
                        "confidence": confidence
                    }
                    if extra_info:
                        result.update(extra_info)
                    results.append(result)
            
            return results

        # Analyze all transactions
        potential_sred = []
        
        for entry in journal_entries:
            for line in entry.Line:
                description = getattr(line, "Description", "")
                amount = getattr(line, "Amount", 0)
                account = getattr(line.AccountRef, "name", "Unknown") if hasattr(line, "AccountRef") else "Unknown"
                
                results = analyze_transaction(
                    "Journal Entry",
                    entry.TxnDate,
                    description,
                    amount,
                    {"account": account}
                )
                potential_sred.extend(results)
        
        for bill in bills:
            description = getattr(bill, "Description", "")
            amount = getattr(bill, "TotalAmt", 0)
            vendor = getattr(bill.VendorRef, "name", "Unknown") if hasattr(bill, "VendorRef") else "Unknown"
            
            results = analyze_transaction(
                "Bill",
                bill.TxnDate,
                description,
                amount,
                {"vendor": vendor}
            )
            potential_sred.extend(results)
        
        # Sort by confidence score and date
        potential_sred.sort(key=lambda x: (-x["confidence"], x["date"]))
        
        # Calculate totals by category
        category_totals = {}
        for item in potential_sred:
            category = item["category"]
            if category not in category_totals:
                category_totals[category] = 0
            category_totals[category] += item["amount"] * item["confidence"]
        
        # Format the result
        result_text = f"SR&ED Analysis Report ({start_date} to {end_date})\n\n"
        
        # Summary by category
        result_text += "Summary by Category:\n"
        total_potential = 0
        for category, amount in category_totals.items():
            result_text += f"{category}: ${amount:,.2f}\n"
            total_potential += amount
        result_text += f"\nTotal Potential SR&ED Expenses: ${total_potential:,.2f}\n"
        
        # Detailed findings
        result_text += "\nDetailed Findings:\n"
        for item in potential_sred:
            result_text += f"\nCategory: {item['category']}\n"
            result_text += f"Confidence Score: {item['confidence']:.1%}\n"
            result_text += f"Date: {item['date']}\n"
            result_text += f"Type: {item['type']}\n"
            result_text += f"Description: {item['description']}\n"
            result_text += f"Amount: ${item['amount']:,.2f}\n"
            if "account" in item:
                result_text += f"Account: {item['account']}\n"
            if "vendor" in item:
                result_text += f"Vendor: {item['vendor']}\n"
            result_text += "-" * 50
        
        result_text += "\n\nNote: This analysis uses AI-based pattern matching to identify potential SR&ED activities. "
        result_text += "Please review with your SR&ED consultant for final eligibility determination."
        
    except Exception as e:
        logger.error("Exception in SR&ED analysis: %s", str(e))
        logger.exception("Full traceback:")
        return [TextContent(type="text", text=f"Error analyzing SR&ED expenses: {str(e)}")]
    
    return [TextContent(type="text", text=result_text)]

async def handle_analyze_cash_flow(server, arguments: dict) -> List[TextContent]:
    """Analyze cash flow trends and patterns"""
    start_date = datetime.strptime(arguments["start_date"], "%Y-%m-%d")
    end_date = datetime.strptime(arguments["end_date"], "%Y-%m-%d")
    group_by = arguments.get("group_by", "month")
    
    qb_client = await create_quickbooks_client(server.user_id)
    
    # Get all payments and bills in the date range
    payments = Payment.all(qb=qb_client)
    bills = Bill.all(qb=qb_client)
    
    # Filter by date range
    payments = [p for p in payments if start_date <= datetime.strptime(p.TxnDate, "%Y-%m-%d") <= end_date]
    bills = [b for b in bills if start_date <= datetime.strptime(b.TxnDate, "%Y-%m-%d") <= end_date]
    
    # Group transactions by month or quarter
    cash_flow = {}
    for payment in payments:
        date = datetime.strptime(payment.TxnDate, "%Y-%m-%d")
        if group_by == "month":
            key = date.strftime("%Y-%m")
        else:  # quarter
            key = f"{date.year}-Q{(date.month-1)//3 + 1}"
        
        if key not in cash_flow:
            cash_flow[key] = {"inflows": 0, "outflows": 0}
        cash_flow[key]["inflows"] += payment.TotalAmt
    
    for bill in bills:
        date = datetime.strptime(bill.TxnDate, "%Y-%m-%d")
        if group_by == "month":
            key = date.strftime("%Y-%m")
        else:  # quarter
            key = f"{date.year}-Q{(date.month-1)//3 + 1}"
        
        if key not in cash_flow:
            cash_flow[key] = {"inflows": 0, "outflows": 0}
        cash_flow[key]["outflows"] += bill.TotalAmt
    
    # Format results
    result = "Cash Flow Analysis:\n\n"
    for period in sorted(cash_flow.keys()):
        data = cash_flow[period]
        net_cash = data["inflows"] - data["outflows"]
        result += f"Period: {period}\n"
        result += f"Cash Inflows: ${data['inflows']:,.2f}\n"
        result += f"Cash Outflows: ${data['outflows']:,.2f}\n"
        result += f"Net Cash Flow: ${net_cash:,.2f}\n\n"
    
    return [TextContent(type="text", text=result)]

async def handle_find_duplicate_transactions(server, arguments: dict) -> List[TextContent]:
    """Identify potential duplicate transactions"""
    start_date = datetime.strptime(arguments["start_date"], "%Y-%m-%d")
    end_date = datetime.strptime(arguments["end_date"], "%Y-%m-%d")
    amount_threshold = arguments.get("amount_threshold", 100)
    
    qb_client = await create_quickbooks_client(server.user_id)
    
    # Get all payments and bills
    payments = Payment.all(qb=qb_client)
    bills = Bill.all(qb=qb_client)
    
    # Filter by date range and amount threshold
    payments = [p for p in payments 
                if start_date <= datetime.strptime(p.TxnDate, "%Y-%m-%d") <= end_date
                and p.TotalAmt >= amount_threshold]
    bills = [b for b in bills 
             if start_date <= datetime.strptime(b.TxnDate, "%Y-%m-%d") <= end_date
             and b.TotalAmt >= amount_threshold]
    
    # Group transactions by amount and date proximity
    potential_duplicates = []
    
    # Check payments
    for i, p1 in enumerate(payments):
        for p2 in payments[i+1:]:
            if (abs(p1.TotalAmt - p2.TotalAmt) < 0.01 and  # Same amount
                abs((datetime.strptime(p1.TxnDate, "%Y-%m-%d") - 
                     datetime.strptime(p2.TxnDate, "%Y-%m-%d")).days) <= 7):  # Within 7 days
                potential_duplicates.append({
                    "type": "payment",
                    "date1": p1.TxnDate,
                    "date2": p2.TxnDate,
                    "amount": p1.TotalAmt,
                    "customer1": p1.CustomerRef.name if hasattr(p1, "CustomerRef") else "Unknown",
                    "customer2": p2.CustomerRef.name if hasattr(p2, "CustomerRef") else "Unknown"
                })
    
    # Check bills
    for i, b1 in enumerate(bills):
        for b2 in bills[i+1:]:
            if (abs(b1.TotalAmt - b2.TotalAmt) < 0.01 and  # Same amount
                abs((datetime.strptime(b1.TxnDate, "%Y-%m-%d") - 
                     datetime.strptime(b2.TxnDate, "%Y-%m-%d")).days) <= 7):  # Within 7 days
                potential_duplicates.append({
                    "type": "bill",
                    "date1": b1.TxnDate,
                    "date2": b2.TxnDate,
                    "amount": b1.TotalAmt,
                    "vendor1": b1.VendorRef.name if hasattr(b1, "VendorRef") else "Unknown",
                    "vendor2": b2.VendorRef.name if hasattr(b2, "VendorRef") else "Unknown"
                })
    
    # Format results
    result = "Potential Duplicate Transactions:\n\n"
    if not potential_duplicates:
        result += "No potential duplicates found.\n"
    else:
        for dup in potential_duplicates:
            result += f"Type: {dup['type'].title()}\n"
            result += f"Amount: ${dup['amount']:,.2f}\n"
            result += f"Date 1: {dup['date1']}\n"
            result += f"Date 2: {dup['date2']}\n"
            if dup['type'] == 'payment':
                result += f"Customer 1: {dup['customer1']}\n"
                result += f"Customer 2: {dup['customer2']}\n"
            else:
                result += f"Vendor 1: {dup['vendor1']}\n"
                result += f"Vendor 2: {dup['vendor2']}\n"
            result += "\n"
    
    return [TextContent(type="text", text=result)]

async def handle_analyze_customer_payment_patterns(server, arguments: dict) -> List[TextContent]:
    """Analyze customer payment behavior and patterns"""
    customer_id = arguments["customer_id"]
    months = arguments.get("months", 12)
    
    qb_client = await create_quickbooks_client(server.user_id)
    
    # Get customer details
    customer = Customer.get(customer_id, qb=qb_client)
    
    # Get invoices and payments for the customer
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months*30)
    
    invoices = Invoice.all(qb=qb_client)
    payments = Payment.all(qb=qb_client)
    
    # Filter by customer and date range
    customer_invoices = [i for i in invoices 
                        if hasattr(i, "CustomerRef") and i.CustomerRef.value == customer_id
                        and start_date <= datetime.strptime(i.TxnDate, "%Y-%m-%d") <= end_date]
    
    customer_payments = [p for p in payments 
                        if hasattr(p, "CustomerRef") and p.CustomerRef.value == customer_id
                        and start_date <= datetime.strptime(p.TxnDate, "%Y-%m-%d") <= end_date]
    
    # Calculate metrics
    total_invoiced = sum(i.TotalAmt for i in customer_invoices)
    total_paid = sum(p.TotalAmt for p in customer_payments)
    outstanding = total_invoiced - total_paid
    
    # Calculate average days to pay
    days_to_pay = []
    for invoice in customer_invoices:
        invoice_date = datetime.strptime(invoice.TxnDate, "%Y-%m-%d")
        for payment in customer_payments:
            payment_date = datetime.strptime(payment.TxnDate, "%Y-%m-%d")
            if payment_date > invoice_date:
                days = (payment_date - invoice_date).days
                days_to_pay.append(days)
    
    avg_days_to_pay = sum(days_to_pay) / len(days_to_pay) if days_to_pay else 0
    
    # Format results
    result = f"Payment Pattern Analysis for {customer.DisplayName}:\n\n"
    result += f"Analysis Period: Last {months} months\n\n"
    result += f"Total Amount Invoiced: ${total_invoiced:,.2f}\n"
    result += f"Total Amount Paid: ${total_paid:,.2f}\n"
    result += f"Outstanding Balance: ${outstanding:,.2f}\n"
    result += f"Average Days to Pay: {avg_days_to_pay:.1f} days\n\n"
    
    result += "Recent Transactions:\n"
    for invoice in sorted(customer_invoices, key=lambda x: x.TxnDate, reverse=True)[:5]:
        result += f"\nInvoice Date: {invoice.TxnDate}\n"
        result += f"Amount: ${invoice.TotalAmt:,.2f}\n"
        result += f"Status: {'Paid' if invoice.TotalAmt <= total_paid else 'Outstanding'}\n"
    
    return [TextContent(type="text", text=result)]

async def handle_generate_financial_metrics(server, arguments: dict) -> List[TextContent]:
    """Generate key financial metrics and ratios"""
    start_date = datetime.strptime(arguments["start_date"], "%Y-%m-%d")
    end_date = datetime.strptime(arguments["end_date"], "%Y-%m-%d")
    requested_metrics = arguments.get("metrics", ["current_ratio", "gross_margin", "net_margin"])
    
    qb_client = await create_quickbooks_client(server.user_id)
    
    # Get all necessary accounts and transactions
    accounts = Account.all(qb=qb_client)
    invoices = Invoice.all(qb=qb_client)
    bills = Bill.all(qb=qb_client)
    
    # Filter transactions by date range
    invoices = [i for i in invoices if start_date <= datetime.strptime(i.TxnDate, "%Y-%m-%d") <= end_date]
    bills = [b for b in bills if start_date <= datetime.strptime(b.TxnDate, "%Y-%m-%d") <= end_date]
    
    # Calculate metrics
    metrics = {}
    
    if "current_ratio" in requested_metrics:
        # Current Assets / Current Liabilities
        current_assets = sum(a.Balance for a in accounts if a.AccountType == "Current Asset")
        current_liabilities = sum(a.Balance for a in accounts if a.AccountType == "Current Liability")
        metrics["current_ratio"] = current_assets / current_liabilities if current_liabilities != 0 else float('inf')
    
    if "quick_ratio" in requested_metrics:
        # (Current Assets - Inventory) / Current Liabilities
        current_assets = sum(a.Balance for a in accounts if a.AccountType == "Current Asset")
        inventory = sum(a.Balance for a in accounts if a.AccountType == "Inventory")
        current_liabilities = sum(a.Balance for a in accounts if a.AccountType == "Current Liability")
        metrics["quick_ratio"] = (current_assets - inventory) / current_liabilities if current_liabilities != 0 else float('inf')
    
    if "debt_to_equity" in requested_metrics:
        # Total Liabilities / Total Equity
        total_liabilities = sum(a.Balance for a in accounts if a.AccountType in ["Current Liability", "Long Term Liability"])
        total_equity = sum(a.Balance for a in accounts if a.AccountType == "Equity")
        metrics["debt_to_equity"] = total_liabilities / total_equity if total_equity != 0 else float('inf')
    
    if "gross_margin" in requested_metrics:
        # (Revenue - COGS) / Revenue
        revenue = sum(i.TotalAmt for i in invoices)
        cogs = sum(b.TotalAmt for b in bills if hasattr(b, "AccountRef") and b.AccountRef.name == "Cost of Goods Sold")
        metrics["gross_margin"] = (revenue - cogs) / revenue if revenue != 0 else 0
    
    if "operating_margin" in requested_metrics:
        # Operating Income / Revenue
        revenue = sum(i.TotalAmt for i in invoices)
        operating_expenses = sum(b.TotalAmt for b in bills if hasattr(b, "AccountRef") and b.AccountRef.name == "Operating Expenses")
        metrics["operating_margin"] = (revenue - operating_expenses) / revenue if revenue != 0 else 0
    
    if "net_margin" in requested_metrics:
        # Net Income / Revenue
        revenue = sum(i.TotalAmt for i in invoices)
        total_expenses = sum(b.TotalAmt for b in bills)
        metrics["net_margin"] = (revenue - total_expenses) / revenue if revenue != 0 else 0
    
    # Format results
    result = "Financial Metrics Analysis:\n\n"
    result += f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n\n"
    
    for metric in requested_metrics:
        if metric in metrics:
            value = metrics[metric]
            if value == float('inf'):
                result += f"{metric.replace('_', ' ').title()}: N/A (division by zero)\n"
            else:
                result += f"{metric.replace('_', ' ').title()}: {value:.2%}\n"
    
    return [TextContent(type="text", text=result)]

async def handle_send_payment(server, arguments):
    """Handle sending a payment through QuickBooks"""
    logger.debug("Starting payment send with arguments: %s", arguments)
    
    # Validate required parameters
    required_params = ["customer_id", "amount", "payment_method"]
    if not all(k in arguments for k in required_params):
        raise ValueError(f"Missing required parameters: {', '.join(required_params)}")

    customer_id = arguments["customer_id"]
    amount = float(arguments["amount"])
    payment_method = arguments["payment_method"]
    
    try:
        qb_client = await create_quickbooks_client(server.user_id)
        
        # Get customer details to verify existence
        customer = Customer.get(customer_id, qb=qb_client)
        
        # Create payment object
        payment = Payment()
        payment.CustomerRef = {"value": customer_id, "name": customer.DisplayName}
        payment.TotalAmt = amount
        payment.PaymentMethodRef = {"value": payment_method}
        payment.TxnDate = datetime.now().strftime("%Y-%m-%d")
        
        # Save the payment
        created_payment = Payment.create(payment, qb=qb_client)
        
        result_text = (
            f"Payment successfully created:\n"
            f"Customer: {customer.DisplayName}\n"
            f"Amount: ${amount:,.2f}\n"
            f"Payment Method: {payment_method}\n"
            f"Date: {created_payment.TxnDate}\n"
            f"Payment ID: {created_payment.Id}"
        )
        
    except Exception as e:
        logger.error("Exception in sending payment: %s", str(e))
        logger.exception("Full traceback:")
        return [TextContent(type="text", text=f"Error sending payment: {str(e)}")]
    
    return [TextContent(type="text", text=result_text)] 