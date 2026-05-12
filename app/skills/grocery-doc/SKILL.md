---
name: grocery-doc
description: Read and edit the shared grocery doc (Google Doc) — long-term memory for preferences, shopping list, and notes. Load this skill before any shopping session or when the user asks about their list or preferences.
metadata:
  adk_additional_tools:
    - read_gdoc
    - write_gdoc
---

# Grocery Doc

A shared Google Doc that acts as the agent's long-term memory across conversations.

## Structure

The doc has two sections:

```
== NEXT BUY ==
- Oat milk
- Parmigiano

== PREFERENCES ==
Brands: Sterzing Vipiteno yogurt (bianco, ×4-6), ...
Staples every order: yogurt, milk, eggs, ...
Diet: Mediterranean/Italian lean. ...
```

## How to use

### Read
Call `read_gdoc()` to get the full text. Do this before any shopping session.

### Write
Call `write_gdoc(content)` with the complete updated document text.
Always read first, make your changes, then write the full doc back.

## When to edit

| User says | What to do |
|-----------|-----------|
| "add X to the list" | Add item under NEXT BUY |
| "remember X" / "note X" | Add under NEXT BUY or PREFERENCES |
| "I switched to oat milk" | Update the brand in PREFERENCES |
| "stop buying X" | Remove from PREFERENCES |
| Items added to cart | Remove them from NEXT BUY |
| New preference learned | Add to PREFERENCES |

## Order history fallback

If the store API returns no order history, load `references/order_history.md`
from this skill — it contains past orders bootstrapped from email receipts.

## Important
- Keep both sections (NEXT BUY and PREFERENCES) intact when writing.
- This is how you build personalization across conversations — anything you learn about the user's preferences should be saved here.
