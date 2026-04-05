import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
try:
    r = requests.get('https://api.github.com', timeout=10, verify=False)
    print(f"Status (no verify): {r.status_code}")
except Exception as e:
    print(f"Error (no verify): {e}")
