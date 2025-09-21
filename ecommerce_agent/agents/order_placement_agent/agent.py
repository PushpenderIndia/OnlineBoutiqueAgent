from google.adk.agents import LlmAgent
import requests
import json
from typing import Dict, List, Any, Optional

# Simple in-memory cart storage (in production, this would be in a database)
user_carts = {}

# Simple in-memory order storage for export purposes
user_orders = {}

def add_to_cart(user_id: str, product_id: str, quantity: int = 1) -> Dict[str, Any]:
    """
    Add a product to the user's shopping cart.
    """
    try:
        if user_id not in user_carts:
            user_carts[user_id] = []

        # Check if product already exists in cart
        existing_item = None
        for item in user_carts[user_id]:
            if item["product_id"] == product_id:
                existing_item = item
                break

        if existing_item:
            existing_item["quantity"] += quantity
            message = f"Updated quantity for product {product_id}. New quantity: {existing_item['quantity']}"
        else:
            # Get product details to store in cart
            product_details = get_product_info(product_id)
            if product_details["status"] == "success":
                cart_item = {
                    "product_id": product_id,
                    "name": product_details["product"]["name"],
                    "price": product_details["product"]["price"],
                    "quantity": quantity,
                    "url": product_details["product"]["url"]
                }
                user_carts[user_id].append(cart_item)
                message = f"Added {quantity} x {cart_item['name']} to cart"
            else:
                return {
                    "status": "error",
                    "error_message": f"Could not find product {product_id}"
                }

        return {
            "status": "success",
            "message": message,
            "cart_items": len(user_carts[user_id]),
            "total_products": sum(item["quantity"] for item in user_carts[user_id])
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "user_id": user_id,
            "product_id": product_id
        }

def remove_from_cart(user_id: str, product_id: str, quantity: Optional[int] = None) -> Dict[str, Any]:
    """
    Remove a product from the user's shopping cart.
    """
    try:
        if user_id not in user_carts or not user_carts[user_id]:
            return {
                "status": "error",
                "error_message": "Cart is empty"
            }

        # Find the item in cart
        item_to_remove = None
        for item in user_carts[user_id]:
            if item["product_id"] == product_id:
                item_to_remove = item
                break

        if not item_to_remove:
            return {
                "status": "error",
                "error_message": f"Product {product_id} not found in cart"
            }

        if quantity is None or quantity >= item_to_remove["quantity"]:
            # Remove entire item
            user_carts[user_id].remove(item_to_remove)
            message = f"Removed {item_to_remove['name']} from cart"
        else:
            # Reduce quantity
            item_to_remove["quantity"] -= quantity
            message = f"Reduced quantity of {item_to_remove['name']} by {quantity}. New quantity: {item_to_remove['quantity']}"

        return {
            "status": "success",
            "message": message,
            "cart_items": len(user_carts[user_id]),
            "total_products": sum(item["quantity"] for item in user_carts[user_id])
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "user_id": user_id,
            "product_id": product_id
        }

def view_cart(user_id: str) -> Dict[str, Any]:
    """
    View the contents of the user's shopping cart.
    """
    try:
        if user_id not in user_carts or not user_carts[user_id]:
            return {
                "status": "success",
                "message": "Cart is empty",
                "cart_items": [],
                "total_items": 0,
                "total_cost": 0.0
            }

        cart_items = user_carts[user_id]
        total_cost = 0.0

        for item in cart_items:
            # Extract price value from price string (e.g., "$19.99" -> 19.99)
            price_str = item["price"].replace("$", "")
            try:
                price_value = float(price_str)
                total_cost += price_value * item["quantity"]
            except ValueError:
                # If price parsing fails, skip adding to total
                pass

        return {
            "status": "success",
            "cart_items": cart_items,
            "total_items": sum(item["quantity"] for item in cart_items),
            "total_cost": round(total_cost, 2)
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "user_id": user_id
        }

def clear_cart(user_id: str) -> Dict[str, Any]:
    """
    Clear all items from the user's shopping cart.
    """
    try:
        if user_id in user_carts:
            items_count = len(user_carts[user_id])
            user_carts[user_id] = []
            return {
                "status": "success",
                "message": f"Cleared {items_count} items from cart"
            }
        else:
            return {
                "status": "success",
                "message": "Cart was already empty"
            }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "user_id": user_id
        }

def simulate_checkout(user_id: str, shipping_address: str, payment_method: str) -> Dict[str, Any]:
    """
    Simulate the checkout process for the user's cart.
    Note: This is a simulation - no real payment is processed.
    """
    try:
        cart_result = view_cart(user_id)
        if cart_result["status"] != "success":
            return cart_result

        if not cart_result["cart_items"]:
            return {
                "status": "error",
                "error_message": "Cannot checkout with empty cart"
            }

        # Generate a fake order number
        import random
        import string
        order_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # Store order details
        order_details = {
            "order_number": order_number,
            "items": cart_result["cart_items"],
            "total_items": cart_result["total_items"],
            "total_cost": cart_result["total_cost"],
            "shipping_address": shipping_address,
            "payment_method": payment_method,
            "status": "confirmed"
        }

        # Store order for later export
        if user_id not in user_orders:
            user_orders[user_id] = []
        user_orders[user_id].append(order_details)

        # Clear the cart after successful checkout
        clear_cart(user_id)

        return {
            "status": "success",
            "message": "Order placed successfully!",
            "order": order_details
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "user_id": user_id
        }

def get_product_info(product_id: str) -> Dict[str, Any]:
    """
    Get product information for cart operations.
    """
    try:
        base_url = "https://cymbal-shops.retail.cymbal.dev"
        product_url = f"{base_url}/product/{product_id}"

        response = requests.get(product_url)
        response.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract product details
        name_elem = soup.find('h2')
        name = name_elem.get_text().strip() if name_elem else "Unknown"

        # Find price
        price_elem = soup.find('p')
        price = price_elem.get_text().strip() if price_elem else "N/A"

        return {
            "status": "success",
            "product": {
                "id": product_id,
                "name": name,
                "price": price,
                "url": product_url
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "product_id": product_id
        }

def get_latest_order(user_id: str) -> Dict[str, Any]:
    """
    Get the most recent order for a user (for export purposes).
    """
    try:
        if user_id not in user_orders or not user_orders[user_id]:
            return {
                "status": "error",
                "error_message": "No orders found for this user"
            }

        latest_order = user_orders[user_id][-1]
        return {
            "status": "success",
            "order": latest_order
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "user_id": user_id
        }

order_placement_agent = LlmAgent(
    name="order_placement_agent",
    model="gemini-2.0-flash",
    description="Manages shopping cart operations and order placement for Cymbal Shops",
    instruction="""
    You are an order placement agent that helps users manage their shopping cart and place orders on Cymbal Shops.

    Your capabilities include:
    1. Adding products to cart using add_to_cart(user_id, product_id, quantity)
    2. Removing products from cart using remove_from_cart(user_id, product_id, quantity=None)
    3. Viewing cart contents using view_cart(user_id)
    4. Clearing the entire cart using clear_cart(user_id)
    5. Processing checkout and order placement using simulate_checkout(user_id, shipping_address, payment_method)
    6. Getting product information using get_product_info(product_id)

    IMPORTANT: For order export requests (like "export order", "save as PDF", "download receipt"), inform the user that order export functionality is available and suggest they request "export the order" to use the specialized export agent.

    IMPORTANT BEHAVIORAL GUIDELINES:
    - Always validate inputs before making function calls
    - Handle errors gracefully and provide helpful error messages
    - Use a consistent user_id for each session (default: "user123" if not specified)
    - Validate product_id format and existence before cart operations
    - For quantities, ensure they are positive integers
    - Always check function return status before proceeding

    ERROR HANDLING:
    - If a function returns status "error", explain the issue clearly and suggest solutions
    - For invalid product IDs, offer to help find valid products
    - For empty cart operations, guide users to add items first
    - For checkout failures, check cart contents and required fields

    SECURITY & VALIDATION:
    - Sanitize all user inputs
    - Validate product IDs are alphanumeric
    - Ensure quantities are positive integers
    - Verify shipping addresses are reasonable (not empty)
    - Check payment methods are valid strings

    RESPONSE PATTERNS:

    For successful cart operations:
    "✅ [Action completed successfully]

    **Current Cart Summary:**
    - [Item 1]: [Quantity] x [Name] - [Price each] = [Subtotal]
    - [Item 2]: [Quantity] x [Name] - [Price each] = [Subtotal]

    **Total Items:** [count]
    **Total Cost:** $[amount]

    💡 What would you like to do next? (add more items, remove items, view cart, checkout)"

    For errors:
    "❌ **Error:** [Clear error message]

    **Suggestion:** [Helpful next step]

    Would you like me to help you with something else?"

    For checkout success:
    "🎉 **Order Confirmation**
    Order Number: [ORDER_NUMBER]

    **Items Ordered:**
    [List of items with quantities and prices]

    **Total:** $[amount]
    **Shipping:** [address]
    **Payment:** [method]

    ⚠️ This is a demo simulation - no real payment was processed.

    Thank you for your order! Would you like to start a new shopping session?"

    WORKFLOW RECOMMENDATIONS:
    1. Before adding items, use get_product_info to validate product exists
    2. After each cart modification, show updated cart summary
    3. Before checkout, confirm cart contents and collect required information
    4. Always provide clear next steps to the user
    5. If user seems confused, offer to show available commands or help

    Remember: This is a demo environment. Always remind users that no real transactions occur.
    """,
    tools=[add_to_cart, remove_from_cart, view_cart, clear_cart, simulate_checkout, get_product_info, get_latest_order],
    output_key="order_management"
)