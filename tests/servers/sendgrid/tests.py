import os
import pytest
from datetime import datetime, timedelta

# ====================================================================
# IMPORTANT: Replace these email addresses with your verified emails
# SendGrid requires verified sender domains/emails for successful tests
# ====================================================================
VERIFIED_SENDER_EMAIL = "your-verified@example.com"  # CHANGE THIS
TEST_RECIPIENT_EMAIL = "recipient@example.com"
TEST_CONTACT_EMAIL = "test-contact@example.com"


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
        f"If successful, include the statistics in your response. "
        f"If there's an error, respond with 'error: [error message]'."
    )

    # Check response and log it
    assert response, "No response received from get_email_stats tool"
    assert "error:" not in response.lower(), f"Error encountered: {response}"
    print("Get email stats response:")
    print(f"\t{response}")

    # Simple assertion checking for success indicators
    assert any(
        term in response.lower()
        for term in ["statistics", "delivered", "opens", "clicks"]
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
        "Use the list_templates tool to get a list of email templates. "
        "Format the response as a clear list showing each template with its ID and name. "
        "If there's an error, respond with 'error: [error message]'."
    )

    # Check response and log it
    assert response, "No response received from list_templates tool"
    assert "error:" not in response.lower(), f"Error encountered: {response}"
    print("List templates response:")
    print(f"\t{response}")

    # More specific assertion checking for actual template data
    # We can't check for specific template IDs, but we can check for formatting patterns
    template_data_indicators = [
        "id:",
        "name:",
        "generation:",
        "template id",
        "template name",
        "---",  # List separator we expect
        "\n- ",  # Bullet point format
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


@pytest.mark.asyncio
async def test_manage_suppression(client):
    """Test managing the suppression list in SendGrid"""
    # Use the test contact email for suppression testing
    email = TEST_CONTACT_EMAIL

    # Test adding to suppression list
    add_response = await client.process_query(
        f"Use the manage_suppression tool to add the email '{email}' "
        f"to the 'blocks' suppression group. "
        f"If successful, respond with 'Email successfully added to blocks list'. "
        f"If there's an error, respond with 'error: [error message]'."
    )

    # Check response and log it
    assert add_response, "No response received from manage_suppression tool"
    assert "error:" not in add_response.lower(), f"Error encountered: {add_response}"
    print("Manage suppression (add) response:")
    print(f"\t{add_response}")

    # Simple assertion checking for success indicators
    assert any(
        term in add_response.lower() for term in ["successfully", "added", "blocks"]
    ), f"Email was not added to suppression list successfully: {add_response}"

    # Test removing from suppression list
    remove_response = await client.process_query(
        f"Use the manage_suppression tool to remove the email '{email}' "
        f"from the 'blocks' suppression group. "
        f"If successful, respond with 'Email successfully removed from blocks list'. "
        f"If there's an error, respond with 'error: [error message]'."
    )

    # Check response and log it
    assert remove_response, "No response received from manage_suppression tool (remove)"
    assert (
        "error:" not in remove_response.lower()
    ), f"Error encountered: {remove_response}"
    print("Manage suppression (remove) response:")
    print(f"\t{remove_response}")

    # Simple assertion checking for success indicators
    assert any(
        term in remove_response.lower()
        for term in ["successfully", "removed", "blocks"]
    ), f"Email was not removed from suppression list successfully: {remove_response}"

    print("✅ Suppression management tool test completed")
