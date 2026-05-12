---
name: store-api
description: Search products, manage the shopping cart, and view orders on your grocery store. Load this skill before any shopping operation.
metadata:
  adk_additional_tools:
    - store_graphql
---

# Store GraphQL API

Auth and cart ID are handled automatically by the `store_graphql` tool.

## Search products

```graphql
query($search: String!, $pageSize: Int!) {
  products(search: $search, pageSize: $pageSize) {
    total_count
    items {
      name
      sku
      url_key
      stock_status
      price_range {
        maximum_price {
          regular_price { value currency }
        }
      }
    }
  }
}
```
Variables: `{"search": "latte intero", "pageSize": 5}`

Use product names in the store's local language for search terms.

## View cart

The `$cartId` variable is injected automatically.

```graphql
query($cartId: String!) {
  cart(cart_id: $cartId) {
    total_quantity
    items {
      id
      product { name sku }
      quantity
      prices {
        price { value }
        row_total { value }
      }
    }
    prices {
      grand_total { value currency }
    }
  }
}
```
Variables: `{}`  (cartId is auto-injected)

## Add to cart

```graphql
mutation($cartId: String!, $sku: String!, $quantity: Float!) {
  addSimpleProductsToCart(input: {
    cart_id: $cartId
    cart_items: [{ data: { sku: $sku, quantity: $quantity } }]
  }) {
    cart {
      items { product { name sku } quantity }
      prices { grand_total { value currency } }
    }
  }
}
```
Variables: `{"sku": "115091", "quantity": 2}`

## Remove from cart

Use the item `id` from the view cart query (not the product SKU).

```graphql
mutation($cartId: String!, $itemId: Int!) {
  removeItemFromCart(input: { cart_id: $cartId, cart_item_id: $itemId }) {
    cart {
      total_quantity
      items { id product { name } quantity }
    }
  }
}
```
Variables: `{"itemId": 977835}`

## Clear cart

View the cart first, then remove each item by ID.

## View order history

```graphql
query($pageSize: Int!) {
  customer {
    orders(pageSize: $pageSize) {
      items {
        order_number
        order_date
        status
        total { grand_total { value currency } }
        items {
          product_name
          product_sku
          quantity_ordered
          product_sale_price { value }
        }
      }
    }
  }
}
```
Variables: `{"pageSize": 10}`

## Get product details

```graphql
query($sku: String!) {
  products(filter: { sku: { eq: $sku } }) {
    items {
      name
      sku
      description { html }
      stock_status
      categories { name }
      price_range {
        maximum_price {
          regular_price { value currency }
        }
      }
    }
  }
}
```
Variables: `{"sku": "115091"}`

## Tips

- Prices are nested: `price_range.maximum_price.regular_price.value`
- `stock_status` is `IN_STOCK` or `OUT_OF_STOCK`
- Cart item `id` (Int) is different from product `sku` (String)
- For the full field reference, load `references/schema.md`
