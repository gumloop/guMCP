import os
import pytest
from datetime import datetime, timedelta

# ====================================================================
# IMPORTANT: Replace these email addresses with your verified emails
# SendGrid requires verified sender domains/emails for successful tests
# ====================================================================
VERIFIED_SENDER_EMAIL = "jyoti@gumloop.com"
TEST_RECIPIENT_EMAIL = "jyoti@gumloop.com"
TEST_CONTACT_EMAIL = "jyoti@gumloop.com"


@pytest.mark.asyncio
async def test_send_email(client):
    """Test sending an email using SendGrid"""
    from_email = VERIFIED_SENDER_EMAIL
    to_email = TEST_RECIPIENT_EMAIL

    response = await client.process_query(
        f"Use the send_email tool to send an email from {from_email} to {to_email} "
        f"with the subject 'Test Email' and content 'This is a test email.' "
        f"If successful, respond with 'Email sent successfully'. "
        f"If there's an error, respond with 'error: [error message]'."
    )

    # Check response and log it
    assert response, "No response received from send_email tool"
    assert "error:" not in response.lower(), f"Error encountered: {response}"
    print("Send email response:")
    print(f"\t{response}")

    # Simple assertion checking for success indicators
    assert any(
        term in response.lower() for term in ["sent successfully", "email sent"]
    ), f"Email was not sent successfully: {response}"

    print("✅ Email sending tool test completed")


@pytest.mark.asyncio
async def test_get_email_stats(client):
    """Test retrieving email statistics from SendGrid"""
    # Get stats for the last 30 days
    today = datetime.now().strftime("%Y-%m-%d")
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    response = await client.process_query(
        f"Use the get_email_stats tool to get email statistics from {thirty_days_ago} to {today}. "
        f"Return the raw statistics data without additional commentary."
    )

    # Check response and log it
    assert response, "No response received from get_email_stats tool"
    assert "error:" not in response.lower(), f"Error encountered: {response}"
    print("Get email stats response:")
    print(f"\t{response}")

    # More specific assertion checking for expected data format
    assert any(
        term in response.lower()
        for term in ["date:", "delivered:", "opens:", "clicks:", "bounces:"]
    ), f"Statistics were not retrieved successfully: {response}"

    print("✅ Email statistics tool test completed")


@pytest.mark.asyncio
async def test_create_template(client):
    """Test creating a template in SendGrid"""
    template_name = f"Test Template {datetime.now().strftime('%Y%m%d%H%M%S')}"

    response = await client.process_query(
        f"Use the create_template tool to create a new email template named '{template_name}' "
        f"with subject 'Test Subject' and HTML content '<h1>Hello {{{{name}}}}</h1><p>This is a test.</p>' "
        f"If successful, include the template ID in your response. "
        f"If there's an error, respond with 'error: [error message]'."
    )

    # Check response and log it
    assert response, "No response received from create_template tool"
    assert "error:" not in response.lower(), f"Error encountered: {response}"
    print("Create template response:")
    print(f"\t{response}")

    # Simple assertion checking for success indicators
    assert any(
        term in response.lower()
        for term in ["template created", "template id", "created successfully"]
    ), f"Template was not created successfully: {response}"

    print("✅ Template creation tool test completed")


@pytest.mark.asyncio
async def test_list_templates(client):
    """Test listing templates from SendGrid"""
    response = await client.process_query(
        "Use the list_templates tool to get a list of email templates with page_size 10. "
        "Return the raw templates data without additional commentary. "
        "If there's an error, respond with 'error: [error message]'."
    )

    # Check response and log it
    assert response, "No response received from list_templates tool"
    assert "error:" not in response.lower(), f"Error encountered: {response}"
    print("List templates response:")
    print(f"\t{response}")

    # Skip test if no templates found
    if "no templates found" in response.lower():
        pytest.skip("Test skipped: No templates found in the account")

    # If templates were found, check for expected template data format
    template_data_indicators = [
        "id:",
        "name:",
        "generation:",
        "template id",
        "template name",
        "---",  # List separator we expect
    ]

    assert any(
        indicator in response.lower() for indicator in template_data_indicators
    ), f"Response doesn't contain template data: {response}"

    print("✅ Template listing tool test completed")


@pytest.mark.asyncio
async def test_add_contact(client):
    """Test adding a contact to SendGrid"""
    # Create a unique email to avoid conflicts
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_email = f"test{timestamp}@{TEST_CONTACT_EMAIL.split('@')[1]}"

    response = await client.process_query(
        f"Use the add_contact tool to add a contact with email '{unique_email}', "
        f"first name 'Test', and last name 'User'. "
        f"If successful, respond with 'Contact added successfully'. "
        f"If there's an error, respond with 'error: [error message]'."
    )

    # Check response and log it
    assert response, "No response received from add_contact tool"
    assert "error:" not in response.lower(), f"Error encountered: {response}"
    print("Add contact response:")
    print(f"\t{response}")

    # Simple assertion checking for success indicators
    assert any(
        term in response.lower()
        for term in ["added successfully", "contact created", "contact added"]
    ), f"Contact was not added successfully: {response}"

    print("✅ Contact addition tool test completed")
