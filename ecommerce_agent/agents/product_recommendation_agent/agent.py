from google.adk.agents import LlmAgent
import requests
import json
from typing import Dict, List, Any, Optional

def get_all_products() -> Dict[str, Any]:
    """
    Get all available products from the Cymbal Shops website for recommendation analysis.
    """
    try:
        base_url = "https://cymbal-shops.retail.cymbal.dev"
        response = requests.get(base_url)
        response.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        products = []
        product_links = soup.find_all('a', href=True)

        for link in product_links:
            href = link.get('href')
            if href and href.startswith('/product/'):
                product_id = href.split('/')[-1]

                parent = link.parent
                if parent:
                    text_content = parent.get_text().strip()
                    import re
                    price_match = re.search(r'\$(\d+\.?\d*)', text_content)
                    price = price_match.group(0) if price_match else "N/A"

                    if price_match:
                        name = text_content[:price_match.start()].strip()
                    else:
                        name = text_content

                    if name and name not in ["Hot Products", ""]:
                        # Get additional details for better recommendations
                        product_details = get_product_category(name)

                        product_info = {
                            "id": product_id,
                            "name": name,
                            "price": price,
                            "category": product_details["category"],
                            "price_range": product_details["price_range"],
                            "url": f"{base_url}{href}"
                        }
                        products.append(product_info)

        return {
            "status": "success",
            "total_products": len(products),
            "products": products
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "products": []
        }

def get_product_category(product_name: str) -> Dict[str, str]:
    """
    Categorize products and determine price range for better recommendations.
    """
    product_name_lower = product_name.lower()

    # Define categories and their typical characteristics
    categories = {
        "accessories": ["sunglasses", "watch", "jewelry", "bag", "belt"],
        "clothing": ["tank top", "shirt", "pants", "dress", "jacket"],
        "footwear": ["loafers", "shoes", "boots", "sandals"],
        "home": ["candle holder", "salt", "pepper", "jar", "mug", "hairdryer"],
        "beauty": ["hairdryer", "makeup", "skincare"]
    }

    category = "general"
    for cat, keywords in categories.items():
        if any(keyword in product_name_lower for keyword in keywords):
            category = cat
            break

    # Determine price range
    if "watch" in product_name_lower or "loafers" in product_name_lower:
        price_range = "high"
    elif "hairdryer" in product_name_lower:
        price_range = "medium"
    else:
        price_range = "low"

    return {"category": category, "price_range": price_range}

def recommend_products(user_preferences: str, current_product_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Recommend products based on user preferences, purchase history, or current product.
    """
    try:
        # Get all available products
        all_products_result = get_all_products()
        if all_products_result["status"] != "success":
            return all_products_result

        products = all_products_result["products"]

        if not products:
            return {
                "status": "error",
                "error_message": "No products available for recommendations"
            }

        recommendations = []
        user_preferences_lower = user_preferences.lower()

        # If a current product is provided, find similar products
        if current_product_id:
            current_product = next(
                (p for p in products if p["id"] == current_product_id),
                None
            )

            if current_product:
                # Find products in the same category or complementary items
                for product in products:
                    if (product["id"] != current_product_id and
                        (product["category"] == current_product["category"] or
                         are_complementary_products(current_product, product))):
                        recommendations.append({
                            **product,
                            "reason": f"Similar to {current_product['name']}"
                        })

        # Recommend based on user preferences
        preference_keywords = user_preferences_lower.split()

        # Extract price constraint if mentioned
        max_price = None
        if "under" in user_preferences_lower and "$" in user_preferences_lower:
            import re
            price_match = re.search(r'under\s*\$?(\d+\.?\d*)', user_preferences_lower)
            if price_match:
                max_price = float(price_match.group(1))

        for product in products:
            # Check if product matches preferences
            matches_preference = any(keyword in product["name"].lower() for keyword in preference_keywords)

            # Check price constraint
            meets_price_constraint = True
            if max_price is not None:
                try:
                    product_price = float(product["price"].replace("$", ""))
                    meets_price_constraint = product_price <= max_price
                except:
                    meets_price_constraint = True  # If price parsing fails, include the product

            if matches_preference and meets_price_constraint:
                if not any(r["id"] == product["id"] for r in recommendations):
                    recommendations.append({
                        **product,
                        "reason": f"Matches your interest in {user_preferences}"
                    })

        # If no specific matches, recommend popular items within price constraints
        if not recommendations:
            popular_items = ["Sunglasses", "Watch", "Tank Top", "Mug"]
            for product in products:
                if any(item.lower() in product["name"].lower() for item in popular_items):
                    # Check price constraint for popular items too
                    meets_price_constraint = True
                    if max_price is not None:
                        try:
                            product_price = float(product["price"].replace("$", ""))
                            meets_price_constraint = product_price <= max_price
                        except:
                            meets_price_constraint = True

                    if meets_price_constraint:
                        recommendations.append({
                            **product,
                            "reason": "Popular item within your budget"
                        })

        # Sort by category and price for better presentation
        recommendations = sorted(recommendations, key=lambda x: (x["category"], x["price"]))

        return {
            "status": "success",
            "user_preferences": user_preferences,
            "current_product_id": current_product_id,
            "total_recommendations": len(recommendations),
            "recommendations": recommendations[:8]  # Limit to top 8 recommendations
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "user_preferences": user_preferences
        }

def are_complementary_products(product1: Dict, product2: Dict) -> bool:
    """
    Determine if two products complement each other.
    """
    # Define complementary product relationships
    complements = {
        "accessories": ["clothing", "footwear"],
        "clothing": ["accessories", "footwear"],
        "footwear": ["clothing", "accessories"],
        "home": ["home"],  # Home items go well with other home items
    }

    cat1 = product1.get("category", "general")
    cat2 = product2.get("category", "general")

    return cat2 in complements.get(cat1, [])

product_recommendation_agent = LlmAgent(
    name="product_recommendation_agent",
    model="gemini-2.0-flash",
    description="Provides personalized product recommendations based on user preferences and behavior",
    instruction="""
    You are a product recommendation agent that provides personalized suggestions for users shopping on Cymbal Shops.

    Your capabilities include:
    1. Analyzing user preferences and shopping behavior
    2. Finding complementary products
    3. Recommending products based on current product viewing
    4. Suggesting popular and trending items

    When providing recommendations:
    1. ALWAYS call recommend_products function first to get actual product data
    2. ONLY recommend products that are returned by the recommend_products function
    3. Consider user's stated preferences (style, budget, category interests)
    4. Use the exact product names, prices, IDs, and URLs from the function results
    5. Use the exact reasons provided by the function
    6. Group recommendations by category when possible
    7. Include diverse options across different price ranges
    8. NEVER invent or create fake product data

    Guidelines:
    - Always explain why you're recommending specific products
    - Consider seasonal relevance and trends
    - Balance between similar items and diverse options
    - Prioritize products that complement user's current interests
    - Include product details like price and category

    IMPORTANT: You MUST use the recommend_products function to get actual product data from the Cymbal Shops website.
    NEVER create fake or example product data. Only recommend products that are returned by the recommend_products function.

    Response format:
    "Based on your preferences for [preferences], here are my recommendations from our current inventory:

    **[Category] Items:**
    1. [Actual Product Name from function] - [Actual Price from function]
       Reason: [Actual reason from function]
       Product ID: [Actual ID from function]
       URL: [Actual URL from function]

    2. [Actual Product Name from function] - [Actual Price from function]
       Reason: [Actual reason from function]
       Product ID: [Actual ID from function]
       URL: [Actual URL from function]

    **[Another Category] Items:**
    [Continue with other categories using ONLY actual product data...]

    These recommendations are from our current product catalog and match your preferences."

    Always ask: "Would you like recommendations for any specific category or price range?"
    """,
    tools=[get_all_products, recommend_products],
    output_key="product_recommendations"
)