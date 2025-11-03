from fastapi.testclient import TestClient
from main import create_app
import os

app = create_app()
client = TestClient(app)

payload = {
    "jsonrpc": "2.0",
    "id": "flight001",
    "method": "flight/search",
    "params": {
        "destination": "London",
        "date": "2025-11-10"
    }
}

resp = client.post('/a2a/flight', json=payload)
print('Status:', resp.status_code)
try:
    print(resp.json())
except Exception:
    print(resp.text)
