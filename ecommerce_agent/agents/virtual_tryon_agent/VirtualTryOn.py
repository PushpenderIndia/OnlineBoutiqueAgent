import requests
import time
import os
import uuid
from typing import List, Dict, Any

class VirtualTryOn:
    """
    A class to interact with the fal.ai API to apply eyewear styles to a person's image.

    This class handles the entire process:
    1. Uploading a person's image and a sunglasses style image.
    2. Submitting the processing job with a specific prompt.
    3. Polling for the job's completion status.
    4. Fetching the final, generated images.
    """

    # --- Constants for API endpoints ---
    UPLOAD_INITIATE_URL = "https://rest.alpha.fal.ai/storage/upload/initiate"
    EDIT_URL = "https://queue.fal.run/fal-ai/nano-banana/edit"

    def __init__(self, api_key: str):
        """
        Initializes the VirtualTryOn with the fal.ai API key.

        Args:
            api_key (str): Your secret API key from fal.ai.
        
        Raises:
            ValueError: If the API key is not provided.
        """
        if not api_key:
            raise ValueError("An API key from fal.ai is required.")
        
        self.api_key = api_key
        self.base_headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

    def _get_content_type(self, file_path: str) -> str:
        """Determines the image content type from its file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        content_map = {".jpeg": "image/jpeg", ".jpg": "image/jpeg", ".png": "image/png"}
        return content_map.get(ext, "application/octet-stream")

    def _upload_image(self, image_path: str) -> str:
        """
        Uploads a single image to fal.ai storage.

        Args:
            image_path (str): The local path to the image file.

        Returns:
            str: The public URL of the uploaded image.
        
        Raises:
            requests.exceptions.RequestException: For network or HTTP errors.
            FileNotFoundError: If the image_path is invalid.
        """
        print(f"Uploading image: {image_path}...")
        
        # 1. Initiate the upload to get a dedicated upload URL
        content_type = self._get_content_type(image_path)
        file_name = f"{uuid.uuid4()}{os.path.splitext(image_path)[1]}"
        
        initiate_payload = {"file_name": file_name, "content_type": content_type}
        
        initiate_response = requests.post(
            self.UPLOAD_INITIATE_URL, headers=self.base_headers, json=initiate_payload
        )
        initiate_response.raise_for_status()
        upload_data = initiate_response.json()

        # 2. Upload the actual image file to the received URL
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        upload_response = requests.put(
            upload_data["upload_url"], data=image_bytes, headers={"Content-Type": content_type}
        )
        upload_response.raise_for_status()

        print(f"  > Upload successful: {upload_data['file_url']}")
        return upload_data["file_url"]

    def process(self, person_image_path: str, glasses_image_path: str) -> List[str]:
        """
        Main method to process images and return the styled results.

        Args:
            person_image_path (str): Path to the person's image.
            glasses_image_path (str): Path to the sunglasses style image.

        Returns:
            List[str]: A list of URLs for the generated images, or an empty list on failure.
        """
        try:
            # Step 1: Upload both images
            person_url = self._upload_image(person_image_path)
            glasses_url = self._upload_image(glasses_image_path)
            
            # Step 2: Submit the edit job
            prompt = (
                "You are an expert digital stylist specializing in eyewear. The first image is a person. "
                "The second image is a style sheet of sunglasses from multiple angles. Your task is to "
                "create two photorealistic images of the person wearing the sunglasses. One from a frontal "
                "view, and one from a slight side (three-quarter) view. Ensure the fit, perspective, and "
                "lighting are realistic. Output only the two final edited images."
            )

            payload = {
                "image_urls": [person_url, glasses_url],
                "prompt": prompt,
                "num_images": 2,
                "output_format": "jpeg",
            }

            print("\nSubmitting styling job to the queue...")
            submit_response = requests.post(self.EDIT_URL, headers=self.base_headers, json=payload)
            submit_response.raise_for_status()
            job_data = submit_response.json()
            print(f"  > Job submitted successfully. Request ID: {job_data['request_id']}")

            # Step 3: Poll for job completion
            status_url = job_data["status_url"]
            print("\nPolling for job status...")
            while True:
                status_check = requests.get(status_url, headers=self.base_headers)
                status_check.raise_for_status()
                status_data = status_check.json()
                current_status = status_data["status"]
                
                print(f"  > Current status: {current_status}")

                if current_status == "COMPLETED":
                    break
                elif current_status in ("FAILED", "ERROR"):
                    print("  > Job failed.")
                    # You can inspect status_data['logs'] for more details
                    return []
                
                time.sleep(3)  # Wait for 3 seconds before checking again

            # Step 4: Fetch the final result
            print("\nJob completed! Fetching results...")
            result_response = requests.get(job_data["response_url"], headers=self.base_headers)
            result_response.raise_for_status()
            final_data = result_response.json()

            image_urls = [img["url"] for img in final_data.get("images", [])]
            return image_urls

        except FileNotFoundError as e:
            print(f"\n[ERROR] File not found: {e}")
        except requests.exceptions.RequestException as e:
            print(f"\n[ERROR] An API or network error occurred: {e}")
        except Exception as e:
            print(f"\n[ERROR] An unexpected error occurred: {e}")
        
        return []


if __name__ == "__main__":
    # Fetch API key from environment variable
    FAL_KEY = "f2143c03-df8d-4258-9533-94ea137c2ead:e48f2c11b2bf4c346843d3a54f6e3787" #os.getenv("FAL_API_KEY")

    # Define paths to your images
    PERSON_IMAGE_PATH = "me.jpeg"
    GLASSES_IMAGE_PATH = "sunglasses.jpg"

    # Basic check for setup
    if not FAL_KEY or not os.path.exists(PERSON_IMAGE_PATH) or not os.path.exists(GLASSES_IMAGE_PATH):
        print("="*50)
        print("!!! SETUP REQUIRED !!!")
        print("1. Set the 'FAL_API_KEY' environment variable.")
        print("2. Create a 'person.jpg' file in the same directory.")
        print("3. Create a 'glasses.jpg' file in the same directory.")
        print("="*50)
    else:
        # Create an instance of the styler and run the process
        styler = VirtualTryOn(api_key=FAL_KEY)
        generated_image_urls = styler.process(
            person_image_path=PERSON_IMAGE_PATH,
            glasses_image_path=GLASSES_IMAGE_PATH
        )

        if generated_image_urls:
            print("\n✅ Success! Generated Image URLs:")
            for i, url in enumerate(generated_image_urls, 1):
                print(f"   Image {i}: {url}")
        else:
            print("\n❌ Failure. Could not generate images.")