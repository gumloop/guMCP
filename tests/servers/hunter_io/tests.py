import pytest
import uuid

# ====================== TEST SETUP ======================
# Create a new campaign before running tests
# Add Email Subject Body
# Setup Email Account
# ========================================================

# Global variables to store created IDs
created_lead_id = None
created_list_id = None
campaign_id = None
campaign_recipient_email = f"test_{uuid.uuid4()}@example.com"

# ---------------------- ACCOUNT & ENRICHMENT TOOLS ----------------------


@pytest.mark.asyncio
async def test_account_info(client):
    response = await client.process_query(
        "Use the account_info tool to get your Hunter.io account information. "
        "If successful, start your response with 'Account information fetched successfully'."
    )
    assert (
        "account information fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from account_info"

    print(f"Response: {response}")
    print("✅ account_info passed.")


@pytest.mark.asyncio
async def test_domain_search(client):
    response = await client.process_query(
        "Use the domain_search tool to search for email addresses in domain gumloop.com with limit 3. "
        "If successful, start your response with 'Domain search results fetched successfully'."
    )
    assert (
        "domain search results fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from domain_search"

    print(f"Response: {response}")
    print("✅ domain_search passed.")


@pytest.mark.asyncio
async def test_email_finder(client):
    response = await client.process_query(
        "Use the email_finder tool to find an email address for John Doe at gumloop.com. "
        "If successful, start your response with 'Email finder results fetched successfully'."
    )
    assert (
        "email finder results fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from email_finder"

    print(f"Response: {response}")
    print("✅ email_finder passed.")


@pytest.mark.asyncio
async def test_email_verifier(client):
    response = await client.process_query(
        "Use the email_verifier tool to verify the email address founders@gumloop.com. "
        "If successful, start your response with 'Email verifier results fetched successfully'."
    )
    assert (
        "email verifier results fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from email_verifier"

    print(f"Response: {response}")
    print("✅ email_verifier passed.")


@pytest.mark.asyncio
async def test_email_count(client):
    response = await client.process_query(
        "Use the email_count tool to count email addresses for domain gumloop.com. "
        "If successful, start your response with 'Email count results fetched successfully'."
    )
    assert (
        "email count results fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from email_count"

    print(f"Response: {response}")
    print("✅ email_count passed.")


@pytest.mark.asyncio
async def test_email_enrichment(client):
    response = await client.process_query(
        "Use the email_enrichment tool to get detailed information about email founders@gumloop.com. "
        "If successful, start your response with 'Email enrichment results fetched successfully'."
    )
    assert (
        "email enrichment results fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from email_enrichment"

    print(f"Response: {response}")
    print("✅ email_enrichment passed.")


@pytest.mark.asyncio
async def test_company_enrichment(client):
    response = await client.process_query(
        "Use the company_enrichment tool to get detailed information about company with domain gumloop.com. "
        "If successful, start your response with 'Company enrichment results fetched successfully'."
    )
    assert (
        "company enrichment results fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from company_enrichment"

    print(f"Response: {response}")
    print("✅ company_enrichment passed.")


# ---------------------- LEADS & LISTS CRUD ----------------------


@pytest.mark.asyncio
async def test_create_leads_list(client):
    global created_list_id
    name = f"Test List {uuid.uuid4()}"
    response = await client.process_query(
        f"Use the create_leads_list tool to create a leads list named '{name}'. "
        "If successful, start your response with 'Leads list created successfully' and send me ID in ID: <list_id>."
    )
    assert (
        "leads list created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_leads_list"

    created_list_id = response.lower().split("id: ")[1].split()[0]
    print(f"Response: {response}")
    print("✅ create_leads_list passed.")


@pytest.mark.asyncio
async def test_create_lead(client):
    global created_lead_id
    email = f"test_{uuid.uuid4()}@example.com"
    response = await client.process_query(
        f"Use the create_lead tool to create a lead with email {email}, first name Test, last name User, and company Gumloop. "
        "If successful, start your response with 'Lead created successfully' and send me ID in ID: <lead_id>."
    )
    assert (
        "lead created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_lead"

    created_lead_id = response.lower().split("id: ")[1].split()[0]
    print(f"Response: {response}")
    print("✅ create_lead passed.")


@pytest.mark.asyncio
async def test_list_leads(client):
    response = await client.process_query(
        "Use the list_leads tool to list leads with limit 3. If successful, start your response with 'List of leads fetched successfully'."
    )
    assert (
        "list of leads fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_leads"

    print(f"Response: {response}")
    print("✅ list_leads passed.")


@pytest.mark.asyncio
async def test_get_lead(client):
    if not created_lead_id:
        pytest.skip("No lead ID available")
    response = await client.process_query(
        f"Use the get_lead tool to get lead with ID {created_lead_id}. "
        "If successful, start your response with 'Lead information fetched successfully'."
    )
    assert (
        "lead information fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_lead"

    print(f"Response: {response}")
    print("✅ get_lead passed.")


@pytest.mark.asyncio
async def test_update_lead(client):
    if not created_lead_id:
        pytest.skip("No lead ID available")
    response = await client.process_query(
        f"Use the update_lead tool to update lead {created_lead_id} with new company name 'Updated Company'. "
        "If successful, start your response with 'Lead updated successfully'."
    )
    assert (
        "lead updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_lead"

    print(f"Response: {response}")
    print("✅ update_lead passed.")


@pytest.mark.asyncio
async def test_delete_lead(client):
    if not created_lead_id:
        pytest.skip("No lead ID available")
    response = await client.process_query(
        f"Use the delete_lead tool to delete lead with ID {created_lead_id}. "
        "If successful, start your response with 'Lead deleted successfully'."
    )
    assert (
        "lead deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_lead"

    print(f"Response: {response}")
    print("✅ delete_lead passed.")


@pytest.mark.asyncio
async def test_get_leads_list(client):
    if not created_list_id:
        pytest.skip("No list ID available")
    response = await client.process_query(
        f"Use the get_leads_list tool to get leads list with ID {created_list_id}. "
        "If successful, start your response with 'Leads list fetched successfully'."
    )
    assert (
        "leads list fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_leads_list"

    print(f"Response: {response}")
    print("✅ get_leads_list passed.")


@pytest.mark.asyncio
async def test_update_leads_list(client):
    if not created_list_id:
        pytest.skip("No list ID available")
    new_name = f"Updated List {uuid.uuid4()}"
    response = await client.process_query(
        f"Use the update_leads_list tool to update leads list {created_list_id} with new name '{new_name}'. "
        "If successful, start your response with 'Leads list updated successfully'."
    )
    assert (
        "leads list updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_leads_list"

    print(f"Response: {response}")
    print("✅ update_leads_list passed.")


@pytest.mark.asyncio
async def test_delete_leads_list(client):
    if not created_list_id:
        pytest.skip("No list ID available")
    response = await client.process_query(
        f"Use the delete_leads_list tool to delete leads list with ID {created_list_id}. "
        "If successful, start your response with 'Leads list deleted successfully'."
    )
    assert (
        "leads list deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_leads_list"

    print(f"Response: {response}")
    print("✅ delete_leads_list passed.")


# ---------------------- CAMPAIGN FLOW ----------------------


@pytest.mark.asyncio
async def test_list_campaigns(client):
    global campaign_id

    response = await client.process_query(
        "Use the list_campaigns tool to list all campaigns."
        "If successful, start your response with 'Campaigns fetched successfully'."
        "Send me ID in ID: <campaign_id>."
    )
    assert (
        "campaigns fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_campaigns"

    try:
        campaign_id = response.lower().split("id: ")[1].split()[0]
        print(f"Campaign ID: {campaign_id}")
    except IndexError:
        pytest.fail("No campaign ID found in response")

    print(f"Response: {response}")
    print("✅ list_campaigns passed.")


@pytest.mark.asyncio
async def test_add_campaign_recipients(client):
    global campaign_recipient_email
    if not campaign_id or not created_lead_id:
        pytest.skip("Required IDs missing")
    response = await client.process_query(
        f"Use the add_campaign_recipients tool to add recipients to campaign {campaign_id} "
        f"with emails ['{campaign_recipient_email}'] and lead IDs [{created_lead_id}]. "
        "If successful, start your response with 'Recipients added to campaign successfully'."
    )
    assert (
        "recipients added to campaign successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from add_campaign_recipients"

    print(f"Response: {response}")
    print("✅ add_campaign_recipients passed.")


@pytest.mark.asyncio
async def test_start_campaign(client):
    if not campaign_id:
        pytest.skip("No campaign ID available")
    response = await client.process_query(
        f"Use the start_campaign tool to start campaign with ID {campaign_id}. "
        "If successful, start your response with 'Campaign started successfully'."
    )
    assert (
        "campaign started successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from start_campaign"

    print(f"Response: {response}")
    print("✅ start_campaign passed.")


@pytest.mark.asyncio
async def test_list_leads_lists(client):
    response = await client.process_query(
        "Use the list_leads_lists tool to list all leads lists. "
        "If successful, start your response with 'List of leads lists fetched successfully'."
    )
    assert (
        "list of leads lists fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_leads_lists"

    print(f"Response: {response}")
    print("✅ list_leads_lists passed.")


@pytest.mark.asyncio
async def test_list_campaign_recipients(client):
    if not campaign_id:
        pytest.skip("No campaign ID available")
    response = await client.process_query(
        f"Use the list_campaign_recipients tool to list recipients for campaign {campaign_id}. "
        "If successful, start your response with 'List of campaign recipients fetched successfully'."
    )
    assert (
        "list of campaign recipients fetched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_campaign_recipients"

    print(f"Response: {response}")
    print("✅ list_campaign_recipients passed.")


@pytest.mark.asyncio
async def test_cancel_campaign_recipients(client):
    global campaign_recipient_email
    if not campaign_id:
        pytest.skip("No campaign ID available")

    response = await client.process_query(
        f"Use the cancel_campaign_recipients tool to cancel recipients for campaign {campaign_id} with emails ['{campaign_recipient_email}']. "
        "If successful, start your response with 'Recipients cancelled from campaign successfully'."
    )
    assert (
        "recipients cancelled from campaign successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from cancel_campaign_recipients"

    print(f"Response: {response}")
    print("✅ cancel_campaign_recipients passed.")
