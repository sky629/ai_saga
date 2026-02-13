import asyncio
import os
import sys

from google import genai
from google.genai import types

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import settings


def test_gemini_generation():
    print("Testing Gemini 2.0 Flash Multimodal Generation...")

    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options={"api_version": "v1alpha"},  # Try alpha first
    )

    models_to_test = [
        "gemini-2.0-flash-exp-image-generation",
        "gemini-2.5-flash-image",
        "gemini-3-pro-image-preview",
    ]

    for model_name in models_to_test:
        print(f"\nModel: {model_name}")
        try:
            # For Gemini models, we use generate_content
            response = client.models.generate_content(
                model=model_name,
                contents="Generate a pixel art image of a cat.",
                config=types.GenerateContentConfig(
                    response_modalities=[
                        "IMAGE"
                    ],  # Explicitly ask for IMAGE modality
                ),
            )

            print("Response received.")
            # Check for image parts
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data or part.file_data:
                        print("SUCCESS: Image data found in response!")
                        # print(part) # Debug
                    elif part.text:
                        print(f"Text response: {part.text[:100]}...")
            else:
                print("No content generated.")

        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    test_gemini_generation()
