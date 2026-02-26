import urllib.request
import urllib.error
import json
import os

print("Testing Sprint 4: Atomic Versioning & Compilation Endpoint")

# We will test compiling the existing test_lesson.md
payload = json.dumps({
    "filepath": "01_course/test_lesson.md"
}).encode('utf-8')

req = urllib.request.Request(
    "http://localhost:8000/v1/compile",
    data=payload,
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status Code: {response.getcode()}")
        data = json.loads(response.read().decode())
        print("Success! Compilation Result:")
        print(json.dumps(data, indent=2))
        
        print("\nChecking if JSON file was created in vault...")
        # Inside docker, this is at /vault/01_course/test_lesson.json
        if os.path.exists("/vault/01_course/test_lesson.json"):
            print("Verified: JSON file exists on disk inside vault!")
        else:
            print("Warning: JSON file not found on disk.")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.read().decode()}")
except Exception as e:
    print(f"Connection error: {e}")
