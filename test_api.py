from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("OPENAI_API_KEY")
print(f"Using API key: {api_key[:10]}...")

# Initialize client
client = OpenAI(api_key=api_key)

try:
    # Try a simple completion
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Using a simpler model for testing
        messages=[{"role": "user", "content": "Say hello!"}]
    )
    print("\nAPI Response:")
    print(response.choices[0].message.content)
    print("\nAPI test successful!")
except Exception as e:
    print("\nError:")
    print(str(e))
