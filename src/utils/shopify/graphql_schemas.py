"""
GraphQL queries and mutations for Shopify API
"""

# Products
PRODUCTS_GRAPHQL_QUERY = """
query GetProducts($first: Int!, $query: String, $sortKey: ProductSortKeys, $reverse: Boolean, $after: String, $before: String, $last: Int, $savedSearchId: ID) {
    products(first: $first, query: $query, sortKey: $sortKey, reverse: $reverse, after: $after, before: $before, last: $last, savedSearchId: $savedSearchId) {
        edges {
            cursor
            node {
                id
                title
                description
                handle
                productType
                vendor
                status
                createdAt
                updatedAt
                variants(first: 5) {
                    edges {
                        node {
                            id
                            title
                            price
                            sku
                            inventoryQuantity
                            inventoryItem {
                                id
                            }
                        }
                    }
                }
                images(first: 3) {
                    edges {
                        node {
                            id
                            url
                            altText
                        }
                    }
                }
            }
        }
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
    }
}
"""

PRODUCT_GRAPHQL_QUERY = """
query GetProduct($id: ID!) {
    product(id: $id) {
        id
        title
        description
        handle
        productType
        vendor
        status
        createdAt
        updatedAt
        variants(first: 20) {
            edges {
                node {
                    id
                    title
                    price
                    sku
                    inventoryQuantity
                    inventoryItem {
                        id
                    }
                }
            }
        }
        images(first: 10) {
            edges {
                node {
                    id
                    url
                    altText
                }
            }
        }
    }
}
"""

PRODUCT_CREATE_GRAPHQL_MUTATION = """
mutation productCreate($input: ProductInput!) {
  productCreate(input: $input) {
    product {
      id
      title
      handle
      status
      createdAt
      variants(first: 5) {
        edges {
          node {
            id
            title
            price
            sku
            inventoryQuantity
            inventoryItem {
              id
            }
          }
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

PRODUCT_DELETE_GRAPHQL_MUTATION = """
mutation delete_product($input: ProductDeleteInput!) {
  productDelete(input: $input) {
    deletedProductId
    userErrors {
      field
      message
    }
  }
}
"""

# Shop
SHOP_DETAILS_GRAPHQL_QUERY = """
query get_shop_details {
  shop {
    id
    name
    email
    myshopifyDomain
    url
    plan {
      displayName
      partnerDevelopment
      shopifyPlus
    }
    currencyCode
    currencyFormats {
        moneyFormat
        moneyWithCurrencyFormat
    }
    contactEmail
    ianaTimezone
    billingAddress {
      address1
      address2
      city
      country
      countryCodeV2
      province
      provinceCode
      zip
      phone
      latitude
      longitude
    }
    primaryDomain {
      id
      host
      url
      sslEnabled
    }
  }
}
"""

# Inventory
INVENTORY_LEVEL_GRAPHQL_QUERY = """
query GetInventoryLevel($inventoryItemId: ID!, $locationId: ID) {
  inventoryLevel(inventoryItemId: $inventoryItemId, locationId: $locationId) {
    id
    available
    item {
      id
      inventoryLevels(first: 10) {
        edges {
          node {
            id
            available
            location {
              id
              name
            }
          }
        }
      }
    }
    location {
      id
      name
      isActive
    }
  }
}
"""

INVENTORY_ADJUST_GRAPHQL_MUTATION = """
mutation inventoryAdjustQuantity($input: InventoryAdjustQuantityInput!) {
  inventoryAdjustQuantity(input: $input) {
    inventoryLevel {
      id
      available
    }
    userErrors {
      field
      message
    }
  }
}
"""

INVENTORY_ITEM_UPDATE_GRAPHQL_MUTATION = """
mutation inventoryItemUpdate($inventoryItemId: ID!, $tracked: Boolean!) {
  inventoryItemUpdate(id: $inventoryItemId, input: {tracked: $tracked}) {
    inventoryItem {
      id
      tracked
    }
    userErrors {
      field
      message
    }
  }
}
"""

VARIANT_INVENTORY_ITEM_GRAPHQL_QUERY = """
query GetVariantInventoryItem($variantId: ID!) {
  productVariant(id: $variantId) {
    id
    inventoryItem {
      id
      tracked
      inventoryLevels(first: 5) {
        edges {
          node {
            id
            location {
              id
              name
            }
          }
        }
      }
    }
  }
}
"""
