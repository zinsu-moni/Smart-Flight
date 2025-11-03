"""Simple FlightAgent scaffold.

This agent is intentionally lightweight so importing the module won't require
external dependencies. Implement your real logic inside `find_cheapest`.
"""
from typing import Optional, Dict, Any, List, Tuple
import json
import urllib.request
import urllib.parse
import socket
import os
import requests


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

        # call the finder which may use an external provider
        candidate = self.find_cheapest(query)
        return {
            "status": "ok",
            "query": query,
            "flights": candidate,
        }

    def find_cheapest(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Return a deterministic mock cheapest flight for a given query.

        Query fields used: from, to, date, adults
        """
        # normalize inputs
        origin_input = query.get("from") or query.get("origin") or None
        dest_input = query.get("to") or query.get("destination") or query.get("flight") or None
        date = query.get("date") or "2099-01-01"
        adults = int(query.get("adults") or 1)
        currency = query.get("currency") or "NGN"

        # If origin not provided, try detect via ipapi.co
        origin_city = None
        origin_iata = None
        if not origin_input:
            try:
                r = requests.get("https://ipapi.co/json/", timeout=5)
                ip_info = r.json()
                origin_city = ip_info.get("city")
            except Exception:
                origin_city = None
        else:
            # if user provided an IATA code (3 letters), accept it
            if isinstance(origin_input, str) and len(origin_input) == 3 and origin_input.isalpha():
                origin_iata = origin_input.upper()
            else:
                origin_city = origin_input

        # simple city -> IATA map (extend as needed)
        iata_map = {
            "Lagos": "LOS", "London": "LHR", "Abuja": "ABV",
            "New York": "JFK", "Toronto": "YYZ", "Seoul": "ICN",
            "Los Angeles": "LAX", "San Francisco": "SFO", "Paris": "CDG",
        }

        if origin_city and not origin_iata:
            origin_iata = iata_map.get(origin_city, None)

        # Destination handling: accept IATA or map from name
        dest_iata = None
        if dest_input:
            if isinstance(dest_input, str) and len(dest_input) == 3 and dest_input.isalpha():
                dest_iata = dest_input.upper()
            else:
                dest_iata = iata_map.get(dest_input, None)

        # If still missing IATA codes, fall back to mock behavior
        use_provider = False
        if (self.provider and ("flightapi" in str(self.provider).lower() or str(self.provider).startswith("http"))) or (self.provider_api_key):
            use_provider = True

        results: List[Dict[str, Any]] = []

        if use_provider and self.provider_api_key and origin_iata and dest_iata:
            # call FlightAPI.io onewaytrip endpoint
            try:
                flights = self._call_flightapi_onewaytrip(self.provider_api_key, origin_iata, dest_iata, date, adults, currency)
                if flights:
                    # return top 3 structured flights
                    for f in flights[:3]:
                        results.append(f)
                    return {"origin": origin_city or origin_iata, "destination": dest_input or dest_iata, "flights": results}
            except Exception:
                # fall through to mock candidates
                pass

        # fallback mock deterministic candidates (3 entries)
        seed = sum(ord(c) for c in (str(origin_iata or origin_input or "AAA") + str(dest_iata or dest_input or "BBB")))
        base = (seed % 500) + 50
        for i in range(3):
            price = base + i * 20 + adults * 10
            results.append({
                "airline": f"MockAir{i+1}",
                "price": price,
                "currency": currency,
                "duration": "6h 30m",
                "departure": f"{date}T08:0{i}:00",
                "arrival": f"{date}T14:3{i}:00",
                "stops": 0,
            })

        return {"origin": origin_city or origin_iata or origin_input or "Unknown", "destination": dest_input or dest_iata or "Unknown", "flights": results}

    def _search_provider(self, origin: str, dest: str, date: str, adults: int) -> Optional[Dict[str, Any]]:
        """Best-effort call to an external provider URL.

        We support provider being either a short name (like 'flightapi') or a full URL.
        For the well-known FlightAPI service we call the 'oneway' style endpoint with
        parameters: apikey, from, to, date, adults. If the provider is a custom URL we
        append the same parameters and try to parse JSON for numeric price fields.
        """
        # determine base url
        base = str(self.provider)
        # legacy provider search kept for compatibility - attempt simple GET
        try:
            url = base
            params = {
                "apikey": self.provider_api_key or "",
                "from": origin,
                "to": dest,
                "date": date,
                "adults": str(adults),
            }
            if base.lower() == "flightapi":
                # try a simpler oneway endpoint
                url = f"https://api.flightapi.io/oneway/{self.provider_api_key}/{origin}/{dest}/{date}/{adults}"
            else:
                if "?" in base:
                    url = base + "&" + urllib.parse.urlencode(params)
                else:
                    url = base + "?" + urllib.parse.urlencode(params)

            resp = requests.get(url, headers={"User-Agent": "FlightAgent/1.0"}, timeout=10)
            data = resp.json()

            candidates = self._extract_candidates_from_json(data)
            if candidates:
                candidates.sort(key=lambda c: float(c.get("price", 1e12)))
                return candidates[0]
        except Exception:
            return None

        return None

    def _call_flightapi_onewaytrip(self, api_key: str, origin: str, dest: str, date: str, adults: int, currency: str = "NGN") -> List[Dict[str, Any]]:
        """Call FlightAPI.io onewaytrip endpoint and return a list of structured flight dicts.

        The endpoint pattern used:
        https://api.flightapi.io/onewaytrip/{API_KEY}/{origin}/{destination}/{date}/{adults}/{currency}
        """
        url = f"https://api.flightapi.io/onewaytrip/{api_key}/{origin}/{dest}/{date}/{adults}/{currency}"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "FlightAgent/1.0"})
        resp.raise_for_status()
        data = resp.json()

        results: List[Dict[str, Any]] = []
        # Expected structure: data.data -> list of flights, each with legs
        for flight in data.get("data", [])[:10]:
            try:
                leg = flight.get("legs", [])[0]
                carriers = leg.get("carriers", {})
                marketing = carriers.get("marketing", [])
                airline = marketing[0].get("name") if marketing else carriers.get("summary", "Unknown")
                price_obj = flight.get("price", {}).get("total", {})
                amount = price_obj.get("amount") or price_obj.get("value") or flight.get("price", {}).get("gross")
                results.append({
                    "airline": airline,
                    "price": amount,
                    "currency": flight.get("price", {}).get("total", {}).get("currency") or currency,
                    "duration": leg.get("duration"),
                    "departure": leg.get("departure", {}).get("time"),
                    "arrival": leg.get("arrival", {}).get("time"),
                    "stops": max(0, len(leg.get("segments", [])) - 1),
                })
            except Exception:
                # skip malformed entries
                continue

        return results

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
