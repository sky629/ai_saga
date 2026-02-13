import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.game.infrastructure.adapters.image_service import (
    ImageGenerationServiceAdapter,
)
from config.settings import settings


async def test_image_generation():
    models_to_test = [
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-exp-image-generation",  # Most likely free/experimental
        "imagen-4.0-generate-preview-06-06",
        "imagen-3.0-generate-001",
    ]

    # adapter = ImageGenerationServiceAdapter() # We will instantiate manually to override model

    for model_name in models_to_test:
        print(f"\n--- Testing Model: {model_name} (v1alpha) ---")
        # Temporarily override settings
        settings.image_model = model_name

        # Manually initialize adapter to inject v1alpha config
        import google.genai as genai

        adapter = ImageGenerationServiceAdapter()
        # Override the client with v1alpha
        adapter._genai_client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options={"api_version": "v1alpha"},
        )

        try:
            url = await adapter.generate_image(
                prompt="A pixel art style apple.",
                session_id="test_session",
                user_id="test_user",
            )

            if url:
                print(f"SUCCESS: Image generated with {model_name}!")
                print(f"URL: {url}")
                break  # Stop on first success
            else:
                print(f"FAILURE: {model_name} returned None")

        except Exception as e:
            print(f"ERROR with {model_name}: {e}")


if __name__ == "__main__":
    asyncio.run(test_image_generation())
