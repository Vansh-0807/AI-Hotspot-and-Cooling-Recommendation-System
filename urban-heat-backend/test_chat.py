import httpx
import sys

def test_chat():
    api_key = "iC7Y5AMhS5jozGDWew07CxFVq7heeP5x"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "mistral-small-latest",
        "messages": [{"role": "user", "content": "Test message"}],
        "temperature": 0.5,
        "max_tokens": 300,
    }
    try:
        response = httpx.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload, timeout=10)
        print(response.status_code)
        print(response.text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_chat()
