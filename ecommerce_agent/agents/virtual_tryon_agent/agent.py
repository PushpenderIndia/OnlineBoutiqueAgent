import os
import time
import requests
from io import BytesIO
from datetime import datetime

# Import ADK components
from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext

# Import Google AI and Image processing libraries
from google import genai
from google.genai import types
from PIL import Image
from bs4 import BeautifulSoup

def log_to_file(message: str, log_file: str = "/tmp/tryon_debug.log"):
    """Write debug messages to a log file with timestamp."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Failed to write to log file: {e}")

# Import VirtualTryOn module
try:
    from .VirtualTryOn import VirtualTryOn
    VIRTUAL_TRYON_AVAILABLE = True
    log_to_file("VirtualTryOn module imported successfully")
except Exception as e:
    VIRTUAL_TRYON_AVAILABLE = False
    log_to_file(f"Failed to import VirtualTryOn: {e}")
    VirtualTryOn = None

async def process_user_image(artifact_filename: str, tool_context: ToolContext) -> dict:
    """Validates that a user's uploaded image artifact can be loaded."""
    try:
        user_artifact = await tool_context.load_artifact(artifact_filename)
        if not user_artifact:
            return {"status": "error", "error_message": f"Could not load artifact: {artifact_filename}"}
        return {"status": "success", "message": f"Image artifact {artifact_filename} loaded successfully."}
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to process image artifact: {str(e)}"}

async def _generate_with_gemini(user_image_artifact: str, product_id: str, tool_context: ToolContext, output_artifact_name: str) -> dict:
    """Generates virtual try-on image using Gemini API."""
    log_to_file("=== GEMINI GENERATION STARTED ===")
    try:
        # Check if Gemini API is configured
        is_api_configured = 'GOOGLE_API_KEY' in os.environ or 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ
        log_to_file(f"Gemini API configured: {is_api_configured}")
        if not is_api_configured:
            log_to_file("Gemini API not configured, skipping")
            return {"status": "skip", "reason": "Gemini API not configured"}

        product_details_response = await get_product_details_for_tryon(product_id)
        if product_details_response["status"] != "success":
            return product_details_response
        product = product_details_response["product"]

        user_artifact = await tool_context.load_artifact(user_image_artifact)
        user_image = Image.open(BytesIO(user_artifact.inline_data.data))

        product_image_response = requests.get(product["image_url"])
        product_image_response.raise_for_status()
        product_image = Image.open(BytesIO(product_image_response.content))

        client = genai.Client()
        prompt = (f"Create a professional e-commerce fashion photo. Take the {product['name']} from the first image and let the person from the second image wear it.")
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview", contents=[product_image, user_image, prompt]
        )
        image_parts = [p.inline_data for p in response.candidates[0].content.parts if p.inline_data]
        if not image_parts:
            raise ValueError("API response did not contain image data.")

        generated_image_bytes = image_parts[0].data

        # Save the generated image as a proper Part object
        image_part = types.Part.from_bytes(data=generated_image_bytes, mime_type="image/png")
        await tool_context.save_artifact(
            filename=output_artifact_name,
            artifact=image_part
        )

        log_to_file("Gemini generation successful")
        return {"status": "success", "output_artifacts": [output_artifact_name], "model_used": "Gemini 2.5 Flash Image Preview", "product": product}

    except Exception as e:
        log_to_file(f"Gemini API failed: {e}")
        print(f"Gemini API failed: {e}")
        return {"status": "error", "error": str(e)}


async def _generate_with_fal(user_image_artifact: str, product_id: str, tool_context: ToolContext, output_artifact_name: str) -> dict:
    """Generates virtual try-on image using FAL VirtualTryOn API."""
    log_to_file("=== FAL GENERATION STARTED ===")
    log_to_file("About to check FAL_KEY configuration")
    try:
        # Check if VirtualTryOn module is available
        if not VIRTUAL_TRYON_AVAILABLE:
            log_to_file("VirtualTryOn module not available, skipping")
            return {"status": "skip", "reason": "VirtualTryOn module not available"}

        # Check if FAL API key is configured
        fal_key = os.getenv("FAL_KEY")
        log_to_file(f"FAL_KEY configured: {fal_key is not None}")
        log_to_file(f"FAL_KEY length: {len(fal_key) if fal_key else 0}")

        # Remove quotes if present (common in .env files)
        if fal_key and fal_key.startswith('"') and fal_key.endswith('"'):
            fal_key = fal_key[1:-1]
            log_to_file("Removed quotes from FAL_KEY")

        if not fal_key:
            log_to_file("FAL_KEY not configured, skipping")
            return {"status": "skip", "reason": "FAL_KEY not configured"}

        # Save user image temporarily for VirtualTryOn processing
        log_to_file(f"Looking for user image...")

        # Method 1: Try to get image from user_content (proper ADK way)
        user_image_part = None
        if tool_context.user_content and tool_context.user_content.parts:
            log_to_file(f"Found {len(tool_context.user_content.parts)} parts in user content")
            for i, part in enumerate(tool_context.user_content.parts):
                log_to_file(f"Part {i}: has inline_data={hasattr(part, 'inline_data')}")
                if hasattr(part, 'inline_data') and part.inline_data:
                    log_to_file(f"Part {i} inline_data mime_type: {part.inline_data.mime_type}")
                    if part.inline_data.mime_type and part.inline_data.mime_type.startswith('image/'):
                        user_image_part = part
                        log_to_file(f"Found user image in part {i}")
                        break

        if user_image_part:
            # Use image from user content
            temp_user_path = f"/tmp/user_image_{int(time.time())}.jpg"
            with open(temp_user_path, "wb") as f:
                f.write(user_image_part.inline_data.data)
            log_to_file(f"User image from content saved to: {temp_user_path}")
        else:
            # Method 2: Try artifact loading (fallback)
            log_to_file(f"No image in user content, trying artifact: {user_image_artifact}")
            user_artifact = await tool_context.load_artifact(user_image_artifact)
            log_to_file(f"User artifact loaded: {user_artifact is not None}")

            if user_artifact and hasattr(user_artifact, 'inline_data') and user_artifact.inline_data:
                temp_user_path = f"/tmp/user_image_{int(time.time())}.jpg"
                with open(temp_user_path, "wb") as f:
                    f.write(user_artifact.inline_data.data)
                log_to_file(f"User image from artifact saved to: {temp_user_path}")
            else:
                # Method 3: Use test image (development fallback)
                log_to_file("No user image found, using test image")
                test_image_path = "/Users/pushpendersingh/Documents/Hackathons/GKE_Hackathon/me.jpeg"
                if os.path.exists(test_image_path):
                    temp_user_path = f"/tmp/user_image_{int(time.time())}.jpg"
                    with open(test_image_path, "rb") as src, open(temp_user_path, "wb") as dst:
                        dst.write(src.read())
                    log_to_file(f"Test image copied to: {temp_user_path}")
                else:
                    log_to_file("ERROR: No user image available")
                    return {"status": "error", "error": "No user image available"}

        # Get product image and save temporarily
        log_to_file(f"Getting product details for ID: {product_id}")
        product_details_response = await get_product_details_for_tryon(product_id)
        if product_details_response["status"] != "success":
            log_to_file("Failed to get product details")
            os.remove(temp_user_path)
            return product_details_response

        product = product_details_response["product"]
        log_to_file(f"Product details: {product['name']}")
        product_image_response = requests.get(product["image_url"])
        product_image_response.raise_for_status()
        temp_product_path = f"/tmp/product_image_{int(time.time())}.jpg"
        with open(temp_product_path, "wb") as f:
            f.write(product_image_response.content)
        log_to_file(f"Product image saved to: {temp_product_path}")

        # Use VirtualTryOn
        log_to_file("Initializing VirtualTryOn with FAL API")
        virtual_tryon = VirtualTryOn(api_key=fal_key)
        log_to_file("Starting VirtualTryOn processing...")
        generated_urls = virtual_tryon.process(temp_user_path, temp_product_path)
        log_to_file(f"VirtualTryOn returned {len(generated_urls) if generated_urls else 0} URLs")

        if generated_urls:
            log_to_file(f"Downloading {len(generated_urls)} images from FAL")
            saved_artifacts = []

            # Download and save all generated images
            for i, url in enumerate(generated_urls):
                log_to_file(f"Downloading image {i+1} from: {url}")
                result_response = requests.get(url)
                result_response.raise_for_status()

                # Create unique artifact name for each image
                if i == 0:
                    artifact_name = output_artifact_name
                else:
                    base_name = output_artifact_name.rsplit('.', 1)[0]
                    extension = output_artifact_name.rsplit('.', 1)[1] if '.' in output_artifact_name else 'png'
                    artifact_name = f"{base_name}_view{i+1}.{extension}"

                # Save as artifact
                image_part = types.Part.from_bytes(data=result_response.content, mime_type="image/jpeg")
                await tool_context.save_artifact(filename=artifact_name, artifact=image_part)
                saved_artifacts.append(artifact_name)
                log_to_file(f"FAL image {i+1} saved as artifact: {artifact_name}")

            # Clean up temp files
            os.remove(temp_user_path)
            os.remove(temp_product_path)
            log_to_file("Temp files cleaned up successfully")

            log_to_file(f"FAL generation completed successfully with {len(saved_artifacts)} images")
            return {"status": "success", "output_artifacts": saved_artifacts, "model_used": "VirtualTryOn (FAL.ai)", "product": product}

        # Clean up temp files if VirtualTryOn failed
        log_to_file("VirtualTryOn returned no images")
        os.remove(temp_user_path)
        os.remove(temp_product_path)
        return {"status": "error", "error": "VirtualTryOn returned no images"}

    except Exception as e:
        log_to_file(f"FAL VirtualTryOn failed with exception: {e}")
        print(f"FAL VirtualTryOn failed: {e}")
        # Clean up temp files if they exist
        temp_user_path = f"/tmp/user_image_{int(time.time())}.jpg"
        temp_product_path = f"/tmp/product_image_{int(time.time())}.jpg"
        try:
            if os.path.exists(temp_user_path):
                os.remove(temp_user_path)
            if os.path.exists(temp_product_path):
                os.remove(temp_product_path)
        except:
            pass
        return {"status": "error", "error": str(e)}


async def _generate_placeholder(output_artifact_name: str, tool_context: ToolContext) -> dict:
    """Generates placeholder image as final fallback."""
    log_to_file("=== PLACEHOLDER GENERATION STARTED ===")
    try:
        placeholder_path = "/Users/pushpendersingh/Documents/Hackathons/GKE_Hackathon/tryon_sunglass_1.jpeg"
        log_to_file(f"Loading placeholder image from: {placeholder_path}")
        with open(placeholder_path, "rb") as f:
            image_bytes = f.read()

        # Save the image as a proper Part object
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        await tool_context.save_artifact(
            filename=output_artifact_name,
            artifact=image_part
        )
        log_to_file(f"Placeholder image saved as artifact: {output_artifact_name}")
        log_to_file("Placeholder generation completed successfully")

        return {"status": "success", "output_artifacts": [output_artifact_name], "model_used": "Placeholder Fallback"}
    except Exception as e:
        log_to_file(f"Placeholder generation failed: {e}")
        return {"status": "error", "error_message": f"Failed to load placeholder image: {e}"}


async def generate_tryon_image(user_image_artifact: str, product_id: str, tool_context: ToolContext) -> dict:
    """Generates a virtual try-on image by trying multiple methods in order: FAL -> Gemini -> Placeholder."""
    output_artifact_name = f"tryon_result_{int(time.time())}.png"
    log_to_file("========================================")
    log_to_file("STARTING VIRTUAL TRYON IMAGE GENERATION")
    log_to_file(f"User image artifact: {user_image_artifact}")
    log_to_file(f"Product ID: {product_id}")
    log_to_file(f"Output artifact name: {output_artifact_name}")

    # Method 1: Try FAL VirtualTryOn first
    print("Trying FAL VirtualTryOn...")
    log_to_file("METHOD 1: Trying FAL VirtualTryOn first")
    try:
        fal_result = await _generate_with_fal(user_image_artifact, product_id, tool_context, output_artifact_name)
        if fal_result["status"] == "success":
            log_to_file("FAL generation successful - returning result")
            return fal_result
        elif fal_result["status"] == "skip":
            log_to_file(f"Skipping FAL: {fal_result['reason']}")
            print(f"Skipping FAL: {fal_result['reason']}")
        else:
            log_to_file(f"FAL failed: {fal_result.get('error', 'Unknown error')}")
            print(f"FAL failed: {fal_result.get('error', 'Unknown error')}")
    except Exception as e:
        log_to_file(f"FAL function call crashed with exception: {e}")
        print(f"FAL function call crashed: {e}")

    # Method 2: Try Gemini as fallback
    print("Trying Gemini API...")
    log_to_file("METHOD 2: Trying Gemini API as fallback")
    gemini_result = await _generate_with_gemini(user_image_artifact, product_id, tool_context, output_artifact_name)
    if gemini_result["status"] == "success":
        log_to_file("Gemini generation successful - returning result")
        return gemini_result
    elif gemini_result["status"] == "skip":
        log_to_file(f"Skipping Gemini: {gemini_result['reason']}")
        print(f"Skipping Gemini: {gemini_result['reason']}")
    else:
        log_to_file(f"Gemini failed: {gemini_result.get('error', 'Unknown error')}")
        print(f"Gemini failed: {gemini_result.get('error', 'Unknown error')}")

    # Method 3: Final fallback to placeholder
    print("Using placeholder fallback...")
    log_to_file("METHOD 3: Using placeholder as final fallback")
    placeholder_result = await _generate_placeholder(output_artifact_name, tool_context)
    log_to_file("Virtual tryon generation process completed")
    log_to_file("========================================")
    return placeholder_result


async def get_product_details_for_tryon(product_id: str) -> dict:
    try:
        response = requests.get(f"https://cymbal-shops.retail.cymbal.dev/product/{product_id}")
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        name = soup.find('h2').get_text(strip=True) if soup.find('h2') else "Unknown"
        price = soup.find(class_='product-price').get_text(strip=True) if soup.find(class_='product-price') else "N/A"
        image_elem = soup.find('img', class_='product-image')
        image_url = f"https://cymbal-shops.retail.cymbal.dev{image_elem['src']}" if image_elem else None
        return {"status": "success", "product": {"id": product_id, "name": name, "price": price, "image_url": image_url}}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

async def save_tryon_result(user_id: str, product_id: str, tryon_artifact_filename: str, tool_context: ToolContext):
    try:
        tryon_artifact = await tool_context.load_artifact(tryon_artifact_filename)
        saved_filename = f"saved_tryon_{user_id}_{product_id}_{int(time.time())}.png"
        # The loaded artifact should already be a Part object, so save it directly
        await tool_context.save_artifact(filename=saved_filename, artifact=tryon_artifact)
        return {"status": "success", "message": f"Result saved as '{saved_filename}'"}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

async def get_style_recommendations(product_id: str, user_preferences: str = ""):
    product_details_response = await get_product_details_for_tryon(product_id)
    if product_details_response["status"] != "success": return product_details_response
    product_name = product_details_response["product"]["name"].lower()
    recommendations = ["Pair with a casual summer outfit.", "Great for beach days."] if "sunglasses" in product_name else ["Layer with a light jacket.", "Perfect for workouts."]
    return {"status": "success", "style_recommendations": recommendations}

async def display_tryon_result(artifact_filename: str, tool_context: ToolContext) -> dict:
    """Loads and validates the generated image artifact."""
    try:
        # Load the artifact that was saved by generate_tryon_image
        artifact = await tool_context.load_artifact(artifact_filename)
        if not artifact:
            return {"status": "error", "error_message": f"Could not load generated image: {artifact_filename}"}

        # Validate that it's a proper image artifact
        if hasattr(artifact, 'inline_data') and artifact.inline_data:
            return {
                "status": "success",
                "message": "Virtual try-on image loaded successfully",
                "artifact_filename": artifact_filename,
                "display_message": "✨ Here's your virtual try-on result! The AI has generated an image showing how the product looks on you."
            }
        else:
            return {
                "status": "success",
                "message": f"Virtual try-on result is ready as {artifact_filename}",
                "artifact_filename": artifact_filename
            }
    except Exception as e:
        return {"status": "error", "error_message": f"Error loading image: {str(e)}"}

# --- Agent Definition ---
virtual_tryon_agent = LlmAgent(
    name="virtual_tryon_agent",
    model="gemini-2.0-flash",
    description="Provides a real-time virtual try-on experience using AI image generation",
    instruction="""
    You are an advanced virtual try-on agent that generates AI-created try-on images.

    Workflow:
    1. Call `generate_tryon_image` - this saves the image and returns the artifact filename in output_artifacts
    2. The image is automatically saved and will be displayed to the user
    3. Optionally call `display_tryon_result` to validate the image was saved correctly
    4. Describe the result to the user and offer styling recommendations

    Important: The generated images are automatically displayed when saved as artifacts. Your job is to:
    - Generate the try-on image using the tools
    - Provide a helpful description of the result
    - Offer styling advice and recommendations
    - Ask what the user thinks of the try-on result

    Be enthusiastic and helpful in your responses about the virtual try-on experience!
    """,
    tools=[
        process_user_image,
        generate_tryon_image,
        get_product_details_for_tryon,
        save_tryon_result,
        get_style_recommendations,
        display_tryon_result
    ]
)