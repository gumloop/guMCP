def format_customer(customer):
    """Format a QuickBooks customer object for display"""
    return {
        "id": customer.Id,
        "display_name": customer.DisplayName,
        "company_name": getattr(customer, "CompanyName", ""),
        "email": (
            getattr(customer.PrimaryEmailAddr, "Address", "")
            if hasattr(customer, "PrimaryEmailAddr")
            else ""
        ),
        "phone": (
            getattr(customer.PrimaryPhone, "FreeFormNumber", "")
            if hasattr(customer, "PrimaryPhone")
            else ""
        ),
        "balance": getattr(customer, "Balance", 0),
    }


def format_invoice(invoice):
    """Format a QuickBooks invoice for display"""
    return {
        "id": invoice.Id,
        "doc_number": getattr(invoice, "DocNumber", ""),
        "customer": (
            getattr(invoice.CustomerRef, "name", "")
            if hasattr(invoice, "CustomerRef")
            else ""
        ),
        "date": getattr(invoice, "TxnDate", ""),
        "due_date": getattr(invoice, "DueDate", ""),
        "total": getattr(invoice, "TotalAmt", 0),
        "balance": getattr(invoice, "Balance", 0),
        "status": "Paid" if getattr(invoice, "Balance", 0) == 0 else "Outstanding",
    }


def format_account(account):
    """Format a QuickBooks account for display"""
    return {
        "id": account.Id,
        "name": account.Name,
        "account_type": account.AccountType,
        "account_sub_type": getattr(account, "AccountSubType", ""),
        "current_balance": getattr(account, "CurrentBalance", 0),
    }
