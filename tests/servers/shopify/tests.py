import pytest
import json
import re


@pytest.mark.asyncio
async def test_product_create_and_fetch_flow(client):
    """Test creating a product and then fetching it with Shopify GraphQL"""
    product_title = "Test Product via GraphQL"
    product_description = "This is a test product created via GraphQL"

    mutation = """
    mutation productCreate($input: ProductInput!) {
      productCreate(input: $input) {
        product {
          id
          title
          description
          handle
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    variables = {
        "input": {
            "title": product_title,
            "descriptionHtml": product_description,
            "productType": "Test",
            "vendor": "Test Vendor",
        }
    }

    create_response = await client.process_query(
        f"Use the graphql tool to create a new product in my Shopify store. "
        f"Use this GraphQL mutation: {mutation} "
        f"And these variables: {json.dumps(variables)} "
        f'Return the product ID with keyword "product_id:" if successful.'
    )

    assert product_title in create_response

    id_pattern = r"(gid://shopify/Product/\d+)"
    id_match = re.search(id_pattern, create_response)

    assert id_match, f"Could not extract product ID from response"
    product_id = id_match.group(1)

    query = """
    query getProduct($id: ID!) {
      product(id: $id) {
        id
        title
        description
        handle
        createdAt
        images(first: 1) {
          edges {
            node {
              url
            }
          }
        }
      }
    }
    """

    fetch_variables = {"id": product_id}

    fetch_response = await client.process_query(
        f"Use the graphql tool to fetch the product I just created with ID {product_id}. "
        f"Use this GraphQL query: {query} "
        f"And these variables: {json.dumps(fetch_variables)} "
        f'Confirm the product title with keyword "found_title:" if successful.'
    )

    assert product_title in fetch_response
    assert product_id in fetch_response
