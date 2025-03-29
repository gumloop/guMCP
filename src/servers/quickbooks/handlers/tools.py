import json
import logging
from datetime import datetime
import requests
from mcp.types import TextContent
from quickbooks.objects.customer import Customer
from quickbooks.objects.journalentry import JournalEntry
from quickbooks.objects.bill import Bill

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

async def validate_company_connection(qb_client):
    """Validate that the user is connected to a company and return company info"""
    from quickbooks.objects.company import CompanyInfo
    
    try:
        company_info = CompanyInfo.all(qb_client)[0]
        logger.info(f"Connected to QuickBooks company: {company_info.CompanyName}")
        return company_info
    except Exception as e:
        logger.error(f"Failed to get company info: {str(e)}")
        raise ValueError(
            "Unable to access company information. Please ensure you're connected to "
            "the correct QuickBooks company. You may need to re-authenticate at "
            "https://app.quickbooks.com and select your company."
        )

async def handle_analyze_sred(server, arguments):
    """Handle SR&ED analysis tool"""
    logger.debug("Starting SR&ED analysis with arguments: %s", arguments)
    
    if not all(k in arguments for k in ["start_date", "end_date"]):
        raise ValueError("Missing required parameters: start_date, end_date")

    start_date = arguments["start_date"]
    end_date = arguments["end_date"]
    keywords = arguments.get("keywords", ["research", "development", "experiment", "testing", "prototype", "engineering"])
    
    try:
        logger.debug("Creating QuickBooks client...")
        qb_client = await create_quickbooks_client(server.user_id)
        
        # Validate company connection first
        company_info = await validate_company_connection(qb_client)
        logger.info(f"Running analysis for company: {company_info.CompanyName}")

        # Get journal entries using the client library
        logger.debug("Fetching journal entries...")
        query = f"SELECT * FROM JournalEntry WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' ORDER BY TxnDate"
        journal_entries = JournalEntry.query(query, qb_client)
        logger.debug("Found %d journal entries", len(list(journal_entries)))
        
        # Get bills using the client library
        logger.debug("Fetching bills...")
        bills = Bill.query(
            f"SELECT * FROM Bill WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' ORDER BY TxnDate",
            qb_client
        )
        logger.debug("Found %d bills", len(list(bills)))
        
        # Analyze transactions for SR&ED potential
        potential_sred = []
        
        # Keywords that might indicate SR&ED
        research_keywords = [
            "research", "development", "experiment", "testing", "prototype",
            "engineering", "scientific", "technical", "innovation", "feasibility",
            "analysis", "design", "development", "engineering", "experimental",
            "investigation", "laboratory", "methodology", "process", "programming",
            "project", "qualification", "quality", "research", "scientific",
            "software", "study", "technical", "technology", "testing", "trial"
        ]
        
        # Add user-provided keywords
        research_keywords.extend(keywords)
        
        # Function to check if a description contains research keywords
        def contains_research_keywords(description):
            if not description:
                return False
            description = description.lower()
            return any(keyword.lower() in description for keyword in research_keywords)
        
        # Analyze journal entries
        for entry in journal_entries:
            for line in entry.Line:
                description = getattr(line, "Description", "")
                amount = getattr(line, "Amount", 0)
                
                if contains_research_keywords(description):
                    potential_sred.append({
                        "type": "Journal Entry",
                        "date": entry.TxnDate,
                        "description": description,
                        "amount": amount,
                        "account": getattr(line.AccountRef, "name", "Unknown") if hasattr(line, "AccountRef") else "Unknown"
                    })
        
        # Analyze bills
        for bill in bills:
            description = getattr(bill, "Description", "")
            amount = getattr(bill, "TotalAmt", 0)
            
            if contains_research_keywords(description):
                potential_sred.append({
                    "type": "Bill",
                    "date": bill.TxnDate,
                    "description": description,
                    "amount": amount,
                    "vendor": getattr(bill.VendorRef, "name", "Unknown") if hasattr(bill, "VendorRef") else "Unknown"
                })
        
        # Sort by date
        potential_sred.sort(key=lambda x: x["date"])
        
        # Calculate totals
        total_amount = sum(item["amount"] for item in potential_sred)
        
        # Format the result
        result_text = f"SR&ED Analysis Report ({start_date} to {end_date})\n\n"
        result_text += f"Total Potential SR&ED Expenses: ${total_amount:,.2f}\n\n"
        result_text += "Potential SR&ED Transactions:\n\n"
        
        for item in potential_sred:
            result_text += f"Date: {item['date']}\n"
            result_text += f"Type: {item['type']}\n"
            result_text += f"Description: {item['description']}\n"
            result_text += f"Amount: ${item['amount']:,.2f}\n"
            if "account" in item:
                result_text += f"Account: {item['account']}\n"
            if "vendor" in item:
                result_text += f"Vendor: {item['vendor']}\n"
            result_text += "-" * 50 + "\n"
        
        result_text += "\nNote: This is a preliminary analysis. Please review these transactions with your SR&ED consultant to determine eligibility."
        
    except Exception as e:
        logger.error("Exception details - Type: %s, Args: %s", type(e), e.args)
        logger.exception("Full traceback for SR&ED analysis error:")
        error_message = str(e)
        logger.error(f"Failed to analyze SR&ED expenses: {error_message}")
        return [TextContent(type="text", text=f"Error analyzing SR&ED expenses: {error_message}")]
    
    return [TextContent(type="text", text=result_text)] 