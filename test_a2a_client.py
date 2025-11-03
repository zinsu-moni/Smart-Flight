from fastapi.testclient import TestClient
from main import create_app
from agents.a2a_client import call_flight_search, send_message_parts
import os

app = create_app()
client = TestClient(app)


def test_jsonrpc_direct():
    """Simulate an AI agent calling the JSON-RPC flight/search method."""
    # We can call the local TestClient directly by posting to the ASGI app
    url = '/a2a/flight'
    payload = {
        "jsonrpc": "2.0",
        "id": "flight001",
        "method": "flight/search",
        "params": {
            "query": {
                "destination": "London",
                "date": "2025-11-10",
                "adults": 1
            }
        }
    }
    resp = client.post(url, json=payload)
    print('JSON-RPC direct status:', resp.status_code)
    print(resp.json())


def test_message_parts_style():
    """Simulate an AI agent sending messages.parts where one part contains data."""
    url = '/a2a/flight'
    payload = {
        "jsonrpc": "2.0",
        "id": "msg-42",
        "method": "message/send",
        "params": {
            "message": {
                "parts": [
                    {"kind": "text", "text": "Please find cheapest flight"},
                    {"kind": "data", "data": {"destination": "LHR", "date": "2025-11-10", "adults": 1}}
                ]
            }
        }
    }
    resp = client.post(url, json=payload)
    print('message.parts status:', resp.status_code)
    print(resp.json())


def test_using_helper_module():
    """Use the helper functions in agents/a2a_client to call the running TestClient app.

    Note: agents.a2a_client performs real HTTP requests. To demonstrate it against
    the TestClient (in-process) we call the app endpoint via the TestClient.
    Here we mimic what an external agent would do by calling the helper but
    direct its URL to the running server address if needed.
    """
    # The helper does real HTTP; if the server runs in another process use http://127.0.0.1:8000/a2a/flight
    # For CI/test here we'll just show how to call it; don't run this helper against TestClient.
    try:
        result = call_flight_search('http://127.0.0.1:8000/a2a/flight', 'London', '2025-11-10', adults=1)
        print('helper client result:', result)
    except Exception as e:
        print('helper client error (expected if server not running on 127.0.0.1:8000):', e)


if __name__ == '__main__':
    test_jsonrpc_direct()
    test_message_parts_style()
    test_using_helper_module()
