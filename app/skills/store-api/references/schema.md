# Store GraphQL Schema Reference

## Product fields

```
products(search: String, filter: ProductFilterInput, pageSize: Int) {
  total_count: Int
  items: [Product] {
    id: Int
    name: String
    sku: String
    url_key: String
    stock_status: ProductStockStatus  # IN_STOCK | OUT_OF_STOCK
    description { html: String }
    small_image { url: String }
    categories: [Category] { name: String }
    price_range {
      maximum_price {
        regular_price { value: Float, currency: String }
      }
    }
  }
}
```

### ProductFilterInput examples

```graphql
# By SKU
products(filter: { sku: { eq: "115091" } }) { ... }

# By category
products(filter: { category_id: { eq: "42" } }) { ... }

# By price range
products(filter: { price: { from: "1.00", to: "5.00" } }) { ... }
```

## Cart fields

```
cart(cart_id: String!) {
  id: String
  total_quantity: Int
  items: [CartItem] {
    id: Int           # Use this for removeItemFromCart
    product {
      name: String
      sku: String
    }
    quantity: Float
    prices {
      price { value: Float, currency: String }
      row_total { value: Float, currency: String }
    }
  }
  prices {
    subtotal_excluding_tax { value: Float, currency: String }
    grand_total { value: Float, currency: String }
  }
}
```

## Customer cart (get or create)

```graphql
{ customerCart { id } }
```

Returns the active cart for the authenticated customer.

## Order fields

```
customer {
  orders(pageSize: Int) {
    items: [Order] {
      id: ID
      order_number: String
      order_date: String
      status: String
      total {
        grand_total { value: Float, currency: String }
      }
      items: [OrderItem] {
        product_name: String
        product_sku: String
        quantity_ordered: Float
        product_sale_price { value: Float, currency: String }
      }
    }
  }
}
```

## Mutations

### addSimpleProductsToCart
```
input: {
  cart_id: String!
  cart_items: [{
    data: {
      sku: String!
      quantity: Float!
    }
  }]
}
```

### removeItemFromCart
```
input: {
  cart_id: String!
  cart_item_id: Int!    # This is the cart item ID, not the product SKU
}
```

### generateCustomerToken (handled automatically)
```
input: {
  email: String!
  password: String!
}
```
