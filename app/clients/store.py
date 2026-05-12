"""GraphQL client for Magento 2 grocery stores."""

import os

import httpx


class StoreClient:
    """Authenticated GraphQL client for a Magento 2 store."""

    GRAPHQL_URL = os.environ.get("STORE_GRAPHQL_URL", "")

    def __init__(self, username: str, password: str, store_code: str = ""):
        self._username = username
        self._password = password
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Content-Type": "application/json",
        }
        if store_code:
            headers["Store"] = store_code
        self._client = httpx.Client(timeout=30.0, headers=headers)
        self._token: str | None = None
        self._cart_id: str | None = None

    def _gql(self, query: str, variables: dict | None = None, _retried: bool = False) -> dict:
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = self._client.post(self.GRAPHQL_URL, json=payload)
        if resp.status_code == 401 and not _retried:
            self._token = None
            self._cart_id = None
            self.login()
            self._ensure_cart()
            return self._gql(query, variables, _retried=True)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RuntimeError(f"GraphQL error: {data['errors']}")
        return data.get("data", {})

    def _ensure_auth(self):
        if not self._token:
            self.login()

    def login(self) -> None:
        data = self._gql(
            """
            mutation generateCustomerToken($email: String!, $password: String!) {
                generateCustomerToken(email: $email, password: $password) {
                    token
                }
            }
            """,
            {"email": self._username, "password": self._password},
        )
        self._token = data["generateCustomerToken"]["token"]
        self._client.headers["Authorization"] = f"Bearer {self._token}"

    def _ensure_cart(self):
        if not self._cart_id:
            data = self._gql("{ customerCart { id } }")
            self._cart_id = data["customerCart"]["id"]

    def search_products(self, query: str, limit: int = 10) -> list[dict]:
        self._ensure_auth()
        data = self._gql(
            """
            query searchProducts($search: String!, $pageSize: Int!) {
                products(search: $search, pageSize: $pageSize) {
                    total_count
                    items {
                        id
                        name
                        sku
                        url_key
                        price_range {
                            maximum_price {
                                regular_price { value currency }
                            }
                        }
                        small_image { url }
                        stock_status
                    }
                }
            }
            """,
            {"search": query, "pageSize": limit},
        )
        items = data.get("products", {}).get("items", [])
        return [
            {
                "id": item["id"],
                "name": item["name"],
                "sku": item["sku"],
                "url_key": item.get("url_key", ""),
                "price": item["price_range"]["maximum_price"]["regular_price"]["value"],
                "currency": item["price_range"]["maximum_price"]["regular_price"]["currency"],
                "image": item.get("small_image", {}).get("url", ""),
                "available": item.get("stock_status") == "IN_STOCK",
            }
            for item in items
        ]

    def get_product_detail(self, sku: str) -> dict:
        self._ensure_auth()
        data = self._gql(
            """
            query getProduct($sku: String!) {
                products(filter: { sku: { eq: $sku } }) {
                    items {
                        id name sku url_key description { html }
                        price_range {
                            maximum_price {
                                regular_price { value currency }
                            }
                        }
                        stock_status
                        categories { id name }
                    }
                }
            }
            """,
            {"sku": sku},
        )
        items = data.get("products", {}).get("items", [])
        return items[0] if items else {}

    def add_to_cart(self, sku: str, quantity: int = 1) -> dict:
        self._ensure_auth()
        self._ensure_cart()
        data = self._gql(
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
                            product { name sku }
                            quantity
                            prices {
                                price { value currency }
                            }
                        }
                        prices {
                            grand_total { value currency }
                        }
                    }
                }
            }
            """,
            {"cartId": self._cart_id, "sku": sku, "quantity": float(quantity)},
        )
        cart = data["addSimpleProductsToCart"]["cart"]
        added = next(
            (i for i in cart["items"] if i["product"]["sku"] == sku), cart["items"][-1]
        )
        return {
            "name": added["product"]["name"],
            "sku": added["product"]["sku"],
            "quantity": added["quantity"],
            "price": added["prices"]["price"]["value"],
        }

    def view_cart(self) -> dict:
        self._ensure_auth()
        self._ensure_cart()
        data = self._gql(
            """
            query getCart($cartId: String!) {
                cart(cart_id: $cartId) {
                    id
                    total_quantity
                    items {
                        id
                        product { name sku }
                        quantity
                        prices {
                            price { value currency }
                            row_total { value currency }
                        }
                    }
                    prices {
                        subtotal_excluding_tax { value currency }
                        grand_total { value currency }
                    }
                }
            }
            """,
            {"cartId": self._cart_id},
        )
        cart = data["cart"]
        return {
            "cart_id": cart["id"],
            "total_quantity": cart["total_quantity"],
            "items": [
                {
                    "id": item["id"],
                    "name": item["product"]["name"],
                    "sku": item["product"]["sku"],
                    "quantity": item["quantity"],
                    "price": item["prices"]["price"]["value"],
                    "row_total": item["prices"]["row_total"]["value"],
                }
                for item in cart["items"]
            ],
            "subtotal": cart["prices"]["subtotal_excluding_tax"]["value"],
            "grand_total": cart["prices"]["grand_total"]["value"],
        }

    def remove_from_cart(self, item_id: str) -> dict:
        self._ensure_auth()
        self._ensure_cart()
        data = self._gql(
            """
            mutation removeItem($cartId: String!, $itemId: Int!) {
                removeItemFromCart(input: { cart_id: $cartId, cart_item_id: $itemId }) {
                    cart {
                        id
                        total_quantity
                        items {
                            id
                            product { name sku }
                            quantity
                        }
                    }
                }
            }
            """,
            {"cartId": self._cart_id, "itemId": int(item_id)},
        )
        return data["removeItemFromCart"]["cart"]

    def get_order_history(self, limit: int = 50) -> list[dict]:
        self._ensure_auth()
        data = self._gql(
            """
            query GetCustomerOrders($pageSize: Int!) {
                customer {
                    orders(pageSize: $pageSize) {
                        total_count
                        items {
                            id
                            order_number
                            order_date
                            status
                            total {
                                grand_total { value currency }
                            }
                            items {
                                product_name
                                product_sku
                                quantity_ordered
                                product_sale_price { value currency }
                            }
                        }
                    }
                }
            }
            """,
            {"pageSize": limit},
        )
        orders = data.get("customer", {}).get("orders", {}).get("items", [])
        return [
            {
                "id": order["id"],
                "order_number": order["order_number"],
                "date": order["order_date"],
                "status": order["status"],
                "total": order["total"]["grand_total"]["value"],
                "items": [
                    {
                        "name": item["product_name"],
                        "sku": item["product_sku"],
                        "quantity": item["quantity_ordered"],
                        "price": item["product_sale_price"]["value"],
                    }
                    for item in order["items"]
                ],
            }
            for order in orders
        ]

    def execute_graphql(self, query: str, variables: dict | None = None) -> dict:
        """Execute an arbitrary GraphQL query or mutation.

        Handles authentication and cart_id injection automatically.
        If the query contains $cartId, the current cart ID is injected.
        """
        self._ensure_auth()
        if variables and "$cartId" in query and "cartId" not in variables:
            self._ensure_cart()
            variables["cartId"] = self._cart_id
        elif "$cartId" in query:
            self._ensure_cart()
            variables = variables or {}
            variables["cartId"] = self._cart_id
        return self._gql(query, variables)

    def close(self):
        self._client.close()
