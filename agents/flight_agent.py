"""Simple FlightAgent scaffold.

This agent is intentionally lightweight so importing the module won't require
external dependencies. Implement your real logic inside `find_cheapest`.
"""
from typing import Optional, Dict, Any, List, Tuple
import json
import urllib.request
import urllib.parse
import socket


class FlightAgent:
    """A tiny agent interface for finding flights.

    Methods:
    - process_messages(messages): Accepts a dict-like query and returns a result dict.
    """

    def __init__(self, provider: Optional[str] = None, provider_api_key: Optional[str] = None) -> None:
        self.provider = provider or "mock"
        self.provider_api_key = provider_api_key

    def cleanup(self) -> None:
        """Clean up any resources (placeholder)."""
        return None

    def process_messages(self, messages: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming messages and return a result dictionary.

        This is a minimal synchronous API suitable for the scaffold. The
        return value should be JSON-serializable.
        """
        # messages is intentionally unstructured in the scaffold; real code should
        # validate and parse the incoming A2A message schema.
        query = messages.get("query") if isinstance(messages, dict) else None
        if not query:
            return {
                "status": "error",
                "message": "no query provided",
            }

        # call a placeholder finder
        candidate = self.find_cheapest(query)
        return {
            "status": "ok",
            "query": query,
            "cheapest": candidate,
        }

    def find_cheapest(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Return a deterministic mock cheapest flight for a given query.

        Query fields used: from, to, date, adults
        """
        origin = query.get("from") or query.get("origin") or "AAA"
        dest = query.get("to") or query.get("destination") or "BBB"
        date = query.get("date") or "2099-01-01"
        adults = int(query.get("adults") or 1)

        # If a provider URL is configured, attempt a best-effort call.
        if self.provider and (self.provider.startswith("http") or "flightapi" in str(self.provider).lower()):
            try:
                candidate = self._search_provider(origin, dest, date, adults)
                if candidate:
                    return candidate
            except Exception:
                # fall back to mock on any provider error
                pass

        # deterministic mock price: ascii-sum of origin+dest mod 500 + 50
        seed = sum(ord(c) for c in (str(origin) + str(dest)))
        price = (seed % 500) + 50 + adults * 10
        booking_link = f"https://example.com/book?from={origin}&to={dest}&date={date}&adults={adults}"

        return {
            "price": price,
            "currency": "USD",
            "airline": "MockAir",
            "booking_link": booking_link,
        }

    def _search_provider(self, origin: str, dest: str, date: str, adults: int) -> Optional[Dict[str, Any]]:
        """Best-effort call to an external provider URL.

        We support provider being either a short name (like 'flightapi') or a full URL.
        For the well-known FlightAPI service we call the 'oneway' style endpoint with
        parameters: apikey, from, to, date, adults. If the provider is a custom URL we
        append the same parameters and try to parse JSON for numeric price fields.
        """
        # determine base url
        base = str(self.provider)
        if base.lower() == "flightapi":
            base = "https://api.flightapi.io/oneway"

        params = {
            "apikey": self.provider_api_key or "",
            "from": origin,
            "to": dest,
            "date": date,
            "adults": str(adults),
        }

        url = base
        if "?" in base:
            url = base + "&" + urllib.parse.urlencode(params)
        else:
            url = base + "?" + urllib.parse.urlencode(params)

        # simple HTTP GET
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FlightAgent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read()
                # try parse as json
                data = json.loads(content.decode("utf-8", errors="ignore"))

                # find all candidate prices in the JSON
                candidates = self._extract_candidates_from_json(data)
                if candidates:
                    # pick cheapest
                    candidates.sort(key=lambda c: float(c.get("price", 1e12)))
                    return candidates[0]
        except (urllib.error.URLError, socket.timeout, ValueError):
            return None

        return None

    def _extract_candidates_from_json(self, data: Any) -> List[Dict[str, Any]]:
        """Recursively scan JSON for price-like fields and return candidate dicts.

        This is a heuristic parser: it looks for dicts containing numeric fields
        named 'price', 'total', 'amount' or similar, and tries to find a booking
        link in nearby string fields.
        """
        candidates: List[Dict[str, Any]] = []

        def walk(obj) -> List[Tuple[Optional[float], Optional[str]]]:
            found: List[Tuple[Optional[float], Optional[str]]] = []
            if isinstance(obj, dict):
                price = None
                link = None
                for k, v in obj.items():
                    key = k.lower()
                    if key in ("price", "total", "amount") and isinstance(v, (int, float)):
                        price = float(v)
                    if isinstance(v, str) and v.startswith("http") and ("book" in v or "purchase" in v or "pay" in v or "/book" in v):
                        link = v
                    # recurse
                    found.extend(walk(v))
                if price is not None:
                    candidates.append({"price": price, "booking_link": link or ""})
            elif isinstance(obj, list):
                for item in obj:
                    found.extend(walk(item))
            return found

        walk(data)
        return candidates
