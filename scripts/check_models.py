
import sys
import os
# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from google import genai
from config.settings import settings

def list_models():
    client = genai.Client(api_key=settings.gemini_api_key)
    print("Listing models with google-genai SDK...")
    
    try:
        # client.models.list() returns an iterator of Model objects
        for m in client.models.list():
            if 'image' in m.name.lower() or 'imagen' in m.name.lower():
                print(f"Model: {m.name}")
                if hasattr(m, 'supported_generation_methods'):
                    print(f"  Methods: {m.supported_generation_methods}")
                if hasattr(m, 'display_name'):
                    print(f"  Display Name: {m.display_name}")
                print("-" * 20)
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
