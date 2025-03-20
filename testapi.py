import requests
import json


def test_huggingface_api():
    API_URL = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": "Hello",
        "parameters": {
            "max_length": 100,
            "temperature": 0.7
        }
    }

    try:
        print("Sending request to HuggingFace API...")
        response = requests.post(API_URL, headers=headers, json=payload)

        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")

        if response.status_code == 200:
            print("\nAPI call successful!")
            print(f"Response: {response.json()}")
            return True
        elif response.status_code == 401:
            print("\nAuthentication failed - Invalid token")
            return False
        elif response.status_code == 429:
            print("\nRate limit exceeded - Too many requests")
            return False
        else:
            print(f"\nUnexpected status code: {response.status_code}")
            print(f"Response content: {response.text}")
            return False

    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        return False


if __name__ == "__main__":
    test_huggingface_api()