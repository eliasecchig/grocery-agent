"""Direct GraphQL API testing against a Magento 2 store.

Usage:
    uv run python scripts/graphql_recon.py <graphql_url> [username] [password]
"""

import json
import os
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("STORE_GRAPHQL_URL", "")
USERNAME = sys.argv[2] if len(sys.argv) > 2 else ""
PASSWORD = sys.argv[3] if len(sys.argv) > 3 else ""

client = httpx.Client(
    timeout=30.0,
    headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Content-Type": "application/json",
    },
)


def gql(query: str, variables: dict | None = None, label: str = ""):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = client.post(BASE, json=payload)
    data = resp.json()
    print(f"\n{'='*60}")
    print(f"=== {label} === (status: {resp.status_code})")
    if "errors" in data:
        print(f"ERRORS: {json.dumps(data['errors'], indent=2)[:500]}")
    if "data" in data:
        print(json.dumps(data["data"], indent=2)[:1000])
    return data


# 1. Login — Magento 2 generateCustomerToken
print("Step 1: Login")
login_data = gql(
    """
    mutation generateCustomerToken($email: String!, $password: String!) {
        generateCustomerToken(email: $email, password: $password) {
            token
        }
    }
    """,
    {"email": USERNAME, "password": PASSWORD},
    "LOGIN",
)

token = None
if "data" in login_data and login_data["data"].get("generateCustomerToken"):
    token = login_data["data"]["generateCustomerToken"]["token"]
    print(f"\nGot token: {token[:20]}...")
    client.headers["Authorization"] = f"Bearer {token}"

# 2. Get customer info
print("\n\nStep 2: Customer info")
gql(
    """
    query {
        customer {
            id
            firstname
            lastname
            email
            addresses {
                id
                city
                street
                postcode
                default_shipping
            }
        }
    }
    """,
    label="CUSTOMER INFO",
)

# 3. Create cart
print("\n\nStep 3: Create cart")
cart_data = gql(
    """
    mutation {
        cartId: createEmptyCart
    }
    """,
    label="CREATE CART",
)
cart_id = cart_data.get("data", {}).get("cartId", "")
print(f"Cart ID: {cart_id}")

# 4. Search products
print("\n\nStep 4: Search products")
search_data = gql(
    """
    query searchProducts($search: String!, $pageSize: Int!) {
        products(search: $search, pageSize: $pageSize) {
            total_count
            items {
                id
                uid
                name
                sku
                url_key
                price_range {
                    maximum_price {
                        regular_price {
                            value
                            currency
                        }
                    }
                }
                small_image {
                    url
                }
                stock_status
            }
        }
    }
    """,
    {"search": "latte intero", "pageSize": 5},
    "SEARCH: latte intero",
)

# 5. Search another product
gql(
    """
    query searchProducts($search: String!, $pageSize: Int!) {
        products(search: $search, pageSize: $pageSize) {
            total_count
            items {
                id
                name
                sku
                price_range {
                    maximum_price {
                        regular_price {
                            value
                            currency
                        }
                    }
                }
                stock_status
            }
        }
    }
    """,
    {"search": "pasta barilla", "pageSize": 5},
    "SEARCH: pasta barilla",
)

# 6. Add to cart (if we got search results)
if search_data.get("data", {}).get("products", {}).get("items"):
    first_product = search_data["data"]["products"]["items"][0]
    sku = first_product["sku"]
    print(f"\n\nStep 6: Add to cart (SKU: {sku})")
    gql(
        """
        mutation addToCart($cartId: String!, $sku: String!, $quantity: Float!) {
            addSimpleProductsToCart(
                input: {
                    cart_id: $cartId
                    cart_items: [{ data: { sku: $sku, quantity: $quantity } }]
                }
            ) {
                cart {
                    id
                    items {
                        id
                        product {
                            name
                            sku
                        }
                        quantity
                        prices {
                            price {
                                value
                                currency
                            }
                        }
                    }
                    prices {
                        grand_total {
                            value
                            currency
                        }
                    }
                }
            }
        }
        """,
        {"cartId": cart_id, "sku": sku, "quantity": 1.0},
        f"ADD TO CART: {first_product['name']}",
    )

# 7. View cart
print("\n\nStep 7: View cart")
gql(
    """
    query getCart($cartId: String!) {
        cart(cart_id: $cartId) {
            id
            total_quantity
            items {
                id
                product {
                    name
                    sku
                }
                quantity
                prices {
                    price {
                        value
                        currency
                    }
                    row_total {
                        value
                        currency
                    }
                }
            }
            prices {
                subtotal_excluding_tax {
                    value
                    currency
                }
                grand_total {
                    value
                    currency
                }
            }
        }
    }
    """,
    {"cartId": cart_id},
    "VIEW CART",
)

# 8. Remove from cart (clean up)
print("\n\nStep 8: Get order history")
gql(
    """
    query GetCustomerOrders($pageSize: Int!) {
        customer {
            orders(pageSize: $pageSize) {
                items {
                    id
                    order_number
                    order_date
                    status
                    total {
                        grand_total {
                            value
                            currency
                        }
                    }
                    items {
                        product_name
                        product_sku
                        quantity_ordered
                        product_sale_price {
                            value
                            currency
                        }
                    }
                }
                total_count
            }
        }
    }
    """,
    {"pageSize": 10},
    "ORDER HISTORY",
)

client.close()
print("\n\nDone! All endpoints confirmed.")
