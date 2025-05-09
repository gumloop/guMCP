import uuid
import pytest
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test

# Shared context dictionary at module level
SHARED_CONTEXT = {}

TOOL_TESTS = [
    {
        "name": "list_publications",
        "args_template": 'with expand=["stats"] limit=2',
        "expected_keywords": ["data", "publication_id"],
        "regex_extractors": {"publication_id": r"id\":\s*\"(pub_[^\"]+)\""},
        "description": "list BeehiiV publications and extract a publication ID",
    },
    {
        "name": "get_publication",
        "args_template": 'with publication_id="{publication_id}" expand=["stats"]',
        "expected_keywords": ["data", "id", "name"],
        "description": "get a specific BeehiiV publication",
        "depends_on": ["publication_id"],
    },
    {
        "name": "get_referral_program",
        "args_template": 'with publication_id="{publication_id}"',
        "expected_keywords": ["data"],
        "description": "get referral program for a BeehiiV publication",
        "depends_on": ["publication_id"],
    },
    {
        "name": "list_posts",
        "args_template": 'with publication_id="{publication_id}" limit=5 expand=["stats"]',
        "expected_keywords": ["data", "post_id"],
        "regex_extractors": {"post_id": r"id\":\s*\"(post_[^\"]+)\""},
        "description": "list posts for a BeehiiV publication and extract a post ID",
        "depends_on": ["publication_id"],
    },
    {
        "name": "get_post",
        "args_template": 'with publication_id="{publication_id}" post_id="{post_id}" expand=["stats"]',
        "expected_keywords": ["data", "id", "title"],
        "description": "get a specific BeehiiV post",
        "depends_on": ["publication_id", "post_id"],
    },
    # Create and manage custom fields
    {
        "name": "create_custom_field",
        "args_template": 'with publication_id="{publication_id}" kind="string" display="Test Field {random_id}"',
        "expected_keywords": ["data", "id", "custom_field_id"],
        "regex_extractors": {"custom_field_id": r"id\":\s*\"([^\"]+)\""},
        "description": "create a custom field on a BeehiiV publication",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
        "depends_on": ["publication_id"],
    },
    {
        "name": "get_custom_field",
        "args_template": 'with publication_id="{publication_id}" custom_field_id="{custom_field_id}"',
        "expected_keywords": ["data", "id", "kind", "display"],
        "description": "get a specific custom field from a BeehiiV publication",
        "depends_on": ["publication_id", "custom_field_id"],
    },
    {
        "name": "list_custom_fields",
        "args_template": 'with publication_id="{publication_id}" limit=5',
        "expected_keywords": ["data", "limit", "page"],
        "description": "list custom fields on a BeehiiV publication",
        "depends_on": ["publication_id"],
    },
    {
        "name": "update_custom_field",
        "args_template": 'with publication_id="{publication_id}" custom_field_id="{custom_field_id}" display="Updated Field {random_id}"',
        "expected_keywords": ["data", "id", "display"],
        "description": "update a custom field on a BeehiiV publication",
        "depends_on": ["publication_id", "custom_field_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    # Create and manage subscriptions
    {
        "name": "create_subscription",
        "args_template": 'with publication_id="{publication_id}" email="test{random_id}@example.com" send_welcome_email=false custom_fields=[{"name": "First Name", "value": "Test"}]',
        "expected_keywords": ["data", "id", "subscription_id", "email"],
        "regex_extractors": {"subscription_id": r"id\":\s*\"(sub_[^\"]+)\""},
        "description": "create a new subscription for a BeehiiV publication",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
        "depends_on": ["publication_id"],
    },
    {
        "name": "list_subscriptions",
        "args_template": 'with publication_id="{publication_id}" limit=5 expand=["custom_fields", "stats"]',
        "expected_keywords": ["data", "limit", "page"],
        "description": "list subscriptions for a BeehiiV publication",
        "depends_on": ["publication_id"],
    },
    {
        "name": "get_subscription_by_email",
        "args_template": 'with publication_id="{publication_id}" email="test{random_id}@example.com" expand=["custom_fields"]',
        "expected_keywords": ["data", "id", "email"],
        "description": "get a subscription by email from a BeehiiV publication",
        "setup": lambda context: {"random_id": context.get("random_id", str(uuid.uuid4())[:8])},
        "depends_on": ["publication_id"],
    },
    {
        "name": "get_subscription",
        "args_template": 'with publication_id="{publication_id}" subscription_id="{subscription_id}" expand=["custom_fields"]',
        "expected_keywords": ["data", "id", "email"],
        "description": "get a subscription by ID from a BeehiiV publication",
        "depends_on": ["publication_id", "subscription_id"],
    },
    {
        "name": "update_subscription",
        "args_template": 'with publication_id="{publication_id}" subscription_id="{subscription_id}" custom_fields=[{"name": "First Name", "value": "Updated"}]',
        "expected_keywords": ["data", "id"],
        "description": "update a subscription in a BeehiiV publication",
        "depends_on": ["publication_id", "subscription_id"],
    },
    {
        "name": "add_subscription_tag",
        "args_template": 'with publication_id="{publication_id}" subscription_id="{subscription_id}" tags=["test", "newsletter"]',
        "expected_keywords": ["data", "tags"],
        "description": "add tags to a subscription in a BeehiiV publication",
        "depends_on": ["publication_id", "subscription_id"],
    },
    # Create and manage tiers
    {
        "name": "create_tier",
        "args_template": 'with publication_id="{publication_id}" name="Test Tier {random_id}" description="Test tier for API" prices_attributes=[{"currency": "usd", "amount_cents": 500, "interval": "month", "interval_display": "Monthly", "features": ["Test feature 1", "Test feature 2"]}]',
        "expected_keywords": ["data", "id", "tier_id", "name"],
        "regex_extractors": {"tier_id": r"id\":\s*\"(tier_[^\"]+)\""},
        "description": "create a new tier for a BeehiiV publication",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
        "depends_on": ["publication_id"],
    },
    {
        "name": "list_tiers",
        "args_template": 'with publication_id="{publication_id}" expand=["stats", "prices"]',
        "expected_keywords": ["data", "limit", "page"],
        "description": "list tiers for a BeehiiV publication",
        "depends_on": ["publication_id"],
    },
    {
        "name": "get_tier",
        "args_template": 'with publication_id="{publication_id}" tier_id="{tier_id}" expand=["stats", "prices"]',
        "expected_keywords": ["data", "id", "name"],
        "description": "get a specific tier from a BeehiiV publication",
        "depends_on": ["publication_id", "tier_id"],
    },
    {
        "name": "update_tier",
        "args_template": 'with publication_id="{publication_id}" tier_id="{tier_id}" name="Updated Tier {random_id}" description="Updated test tier description"',
        "expected_keywords": ["data", "id", "name"],
        "description": "update an existing tier in a BeehiiV publication",
        "depends_on": ["publication_id", "tier_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    # Automation related operations
    {
        "name": "list_automations",
        "args_template": 'with publication_id="{publication_id}" limit=5',
        "expected_keywords": ["data", "automation_id"],
        "regex_extractors": {"automation_id": r"id\":\s*\"(aut_[^\"]+)\""},
        "description": "list BeehiiV automations for a publication and extract an automation ID",
        "depends_on": ["publication_id"],
    },
    {
        "name": "get_automation",
        "args_template": 'with publication_id="{publication_id}" automation_id="{automation_id}"',
        "expected_keywords": ["data", "id", "status"],
        "description": "get a specific BeehiiV automation",
        "depends_on": ["publication_id", "automation_id"],
    },
    {
        "name": "list_automation_journeys",
        "args_template": 'with publication_id="{publication_id}" automation_id="{automation_id}" limit=5',
        "expected_keywords": ["data", "automation_journey_id"],
        "regex_extractors": {"automation_journey_id": r"id\":\s*\"(aj_[^\"]+)\""},
        "description": "list journeys within a BeehiiV automation and extract a journey ID",
        "depends_on": ["publication_id", "automation_id"],
    },
    {
        "name": "get_automation_journey",
        "args_template": 'with publication_id="{publication_id}" automation_id="{automation_id}" automation_journey_id="{automation_journey_id}"',
        "expected_keywords": ["data", "id", "automation_id"],
        "description": "get a specific BeehiiV automation journey",
        "depends_on": ["publication_id", "automation_id", "automation_journey_id"],
    },
    {
        "name": "add_subscription_to_automation",
        "args_template": 'with publication_id="{publication_id}" automation_id="{automation_id}" email="test{random_id}@example.com" double_opt_override="on"',
        "expected_keywords": ["data", "id", "email", "status"],
        "description": "add a subscription to a BeehiiV automation flow",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
        "depends_on": ["publication_id", "automation_id"],
    },
    # Subscription update management
    {
        "name": "list_subscription_updates",
        "args_template": 'with publication_id="{publication_id}"',
        "expected_keywords": ["data", "update_id"],
        "regex_extractors": {"update_id": r"id\":\s*\"([^\"]+)\""},
        "description": "list subscription updates for a BeehiiV publication and extract an update ID",
        "depends_on": ["publication_id"],
    },
    {
        "name": "get_subscription_update",
        "args_template": 'with publication_id="{publication_id}" update_id="{update_id}"',
        "expected_keywords": ["data", "id", "status"],
        "description": "get a specific subscription update from a BeehiiV publication",
        "depends_on": ["publication_id", "update_id"],
    },
    {
        "name": "update_subscriptions",
        "args_template": 'with publication_id="{publication_id}" subscriptions=[{"subscription_id":"{subscription_id}", "tier": "premium", "custom_fields": [{"name": "Test Field {random_id}", "value": "test_value"}]}]',
        "expected_keywords": ["data", "subscription_update_id"],
        "regex_extractors": {"subscription_update_id": r"subscription_update_id\":\s*\"([^\"]+)\""},
        "description": "bulk update multiple subscriptions fields, including status, custom fields, and tiers",
        "depends_on": ["publication_id", "subscription_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "update_subscriptions_status",
        "args_template": 'with publication_id="{publication_id}" subscription_ids=["{subscription_id}"] new_status="active"',
        "expected_keywords": ["data"],
        "description": "bulk update subscriptions' status",
        "depends_on": ["publication_id", "subscription_id"],
    },
    # Segment management
    {
        "name": "list_segments",
        "args_template": 'with publication_id="{publication_id}" limit=5 expand=["stats"]',
        "expected_keywords": ["data", "segment_id"],
        "regex_extractors": {"segment_id": r"id\":\s*\"(seg_[^\"]+)\""},
        "description": "list segments for a BeehiiV publication and extract a segment ID",
        "depends_on": ["publication_id"],
    },
    {
        "name": "get_segment",
        "args_template": 'with publication_id="{publication_id}" segment_id="{segment_id}" expand=["stats"]',
        "expected_keywords": ["data", "id", "name"],
        "description": "get a specific segment from a BeehiiV publication",
        "depends_on": ["publication_id", "segment_id"],
    },
    {
        "name": "recalculate_segment",
        "args_template": 'with publication_id="{publication_id}" segment_id="{segment_id}"',
        "expected_keywords": ["_status_code"],
        "description": "recalculate a specific segment in a BeehiiV publication",
        "depends_on": ["publication_id", "segment_id"],
    },
    {
        "name": "list_segment_subscribers",
        "args_template": 'with publication_id="{publication_id}" segment_id="{segment_id}" limit=5',
        "expected_keywords": ["data", "limit", "page"],
        "description": "list subscribers in a specific segment from a BeehiiV publication",
        "depends_on": ["publication_id", "segment_id"],
    },
    # Cleanup operations
    {
        "name": "delete_segment",
        "args_template": 'with publication_id="{publication_id}" segment_id="{segment_id}"',
        "expected_keywords": ["_status_code"],
        "description": "delete a segment from a BeehiiV publication",
        "depends_on": ["publication_id", "segment_id"],
    },
    {
        "name": "delete_custom_field",
        "args_template": 'with publication_id="{publication_id}" custom_field_id="{custom_field_id}"',
        "expected_keywords": ["_status_code"],
        "description": "delete a custom field from a BeehiiV publication",
        "depends_on": ["publication_id", "custom_field_id"],
    },
    {
        "name": "delete_subscription",
        "args_template": 'with publication_id="{publication_id}" subscription_id="{subscription_id}"',
        "expected_keywords": ["_status_code"],
        "description": "delete a subscription from a BeehiiV publication",
        "depends_on": ["publication_id", "subscription_id"],
    },
]

@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT

@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_beehiiv_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)

@pytest.mark.asyncio
async def test_resources(client, context):
    response = await run_resources_test(client)
    
    if response and hasattr(response, "resources") and len(response.resources) > 0:
        context["first_resource_uri"] = response.resources[0].uri
    
    return response
