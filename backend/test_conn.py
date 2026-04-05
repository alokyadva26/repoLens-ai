import requests
try:
    r = requests.get('https://api.github.com', timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text[:100]}")
except Exception as e:
    print(f"Error: {e}")
