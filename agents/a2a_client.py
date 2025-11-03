"""Simple A2A JSON-RPC client helpers for calling the /a2a/flight endpoint.

This module provides small helper functions an AI agent (or test harness)
can import and use to call your local Flight Agent service using JSON-RPC
2.0 or the messages.parts A2A style.
"""
from typing import Any, Dict, Optional
import requests
import uuid


def call_flight_search(a2a_url: str, destination: str, date: str, adults: int = 1, origin: Optional[str] = None, currency: str = "NGN", headers: Optional[Dict[str, str]] = None, timeout: int = 10) -> Dict[str, Any]:
    """Call the /a2a/flight endpoint using JSON-RPC 2.0 and a params.query payload.

    Returns the parsed JSON-RPC response 'result' field or raises on error.
    """
    rpc_id = str(uuid.uuid4())
    payload = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": "flight/search",
        "params": {
            "query": {
                "destination": destination,
                "date": date,
                "adults": adults,
                "currency": currency,
            }
        }
    }
    if origin:
        payload["params"]["query"]["from"] = origin

    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)

    resp = requests.post(a2a_url, json=payload, headers=hdrs, timeout=timeout)
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:
        raise RuntimeError(f"A2A RPC error: {body['error']}")
    return body.get("result")


def send_message_parts(a2a_url: str, data: Dict[str, Any], text: Optional[str] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 10) -> Dict[str, Any]:
    """Call the /a2a/flight endpoint using A2A-style message.parts payload.

    The `data` argument should be a dict that will be sent as a part with kind 'data'.
    """
    rpc_id = str(uuid.uuid4())
    parts = []
    if text:
        parts.append({"kind": "text", "text": text})
    parts.append({"kind": "data", "data": data})

    payload = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": "message/send",
        "params": {
            "message": {"parts": parts}
        }
    }

    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)

    resp = requests.post(a2a_url, json=payload, headers=hdrs, timeout=timeout)
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:
        raise RuntimeError(f"A2A RPC error: {body['error']}")
    return body.get("result")


if __name__ == "__main__":
    print("A2A client helper module. Import and call call_flight_search() or send_message_parts() from your agent.")
