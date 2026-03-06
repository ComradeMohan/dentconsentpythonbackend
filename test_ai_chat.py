import requests

def test_chat():
    url = "http://localhost:8000/api/ai_chat"
    payload = {
        "message": "What is a dental implant?",
        "role": "patient"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_chat()
