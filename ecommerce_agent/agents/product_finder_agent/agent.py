from google.adk.agents import LlmAgent
import requests
import json
from typing import Dict, List, Any

def search_products(query: str) -> Dict[str, Any]:
    """
    Search for products on the Cymbal Shops e-commerce site.
    Uses web scraping to find products matching the search query.
    """
    try:
        base_url = "https://cymbal-shops.retail.cymbal.dev"

        # First get the main page to see all available products
        response = requests.get(base_url)
        response.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all product links and information
        products = []
        product_links = soup.find_all('a', href=True)

        for link in product_links:
            href = link.get('href')
            if href and href.startswith('/product/'):
                # Extract product info from the main page
                product_id = href.split('/')[-1]

                # Find price and name from the link's context
                parent = link.parent
                if parent:
                    text_content = parent.get_text().strip()
                    # Look for price pattern ($XX.XX)
                    import re
                    price_match = re.search(r'\$(\d+\.?\d*)', text_content)
                    price = price_match.group(0) if price_match else "N/A"

                    # Extract product name (text before the price)
                    if price_match:
                        name = text_content[:price_match.start()].strip()
                    else:
                        name = text_content

                    if name and name not in ["Hot Products", ""]:
                        product_info = {
                            "id": product_id,
                            "name": name,
                            "price": price,
                            "url": f"{base_url}{href}"
                        }
                        products.append(product_info)

        # Filter products based on query
        if query:
            query_lower = query.lower()
            filtered_products = []
            for product in products:
                if (query_lower in product['name'].lower() or
                    any(word in product['name'].lower() for word in query_lower.split())):
                    filtered_products.append(product)
            products = filtered_products

        return {
            "status": "success",
            "query": query,
            "total_found": len(products),
            "products": products[:10]  # Limit to top 10 results
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "query": query,
            "products": []
        }

def get_product_details(product_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific product.
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

        # Find description
        description_elem = soup.find_all('p')[1] if len(soup.find_all('p')) > 1 else None
        description = description_elem.get_text().strip() if description_elem else "No description available"

        # Find available quantities from the dropdown
        quantity_select = soup.find('select')
        available_quantities = []
        if quantity_select:
            options = quantity_select.find_all('option')
            available_quantities = [option.get_text().strip() for option in options]

        return {
            "status": "success",
            "product": {
                "id": product_id,
                "name": name,
                "price": price,
                "description": description,
                "available_quantities": available_quantities,
                "url": product_url
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "product_id": product_id
        }

product_finder_agent = LlmAgent(
    name="product_finder_agent",
    model="gemini-2.0-flash",
    description="Finds and searches products on the Cymbal Shops e-commerce website",
    instruction="""
    You are a product finder agent that helps users search for products on the Cymbal Shops e-commerce website.

    Your capabilities include:
    1. Searching for products by name, category, or keywords using the search_products tool
    2. Getting detailed information about specific products using the get_product_details tool

    When a user asks about products:
    1. Use search_products to find relevant products based on their query
    2. If they ask for details about a specific product, use get_product_details with the product ID
    3. Present results in a clear, user-friendly format
    4. Include product names, prices, and descriptions when available
    5. Always provide the product URL for easy access

    Guidelines:
    - Always use the tools to get real-time product information
    - Present results in a structured format
    - If no products are found, suggest alternative search terms
    - Include product IDs for reference
    - Be helpful in suggesting related products

    Response format for search results:
    "Found X products matching your search:

    1. [Product Name] - [Price]
       Description: [Description]
       Product ID: [ID]
       URL: [URL]

    2. [Product Name] - [Price]
       Description: [Description]
       Product ID: [ID]
       URL: [URL]

    ..."

    Always end with: "Would you like more details about any specific product?"
    """,
    tools=[search_products, get_product_details],
    output_key="product_search_results"
)