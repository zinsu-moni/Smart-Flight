# Flight Agent (scaffold)

This is a minimal scaffold for a Flight Agent service.

- `main.py` - safe-to-import module. Call `create_app()` to get a FastAPI app.
- `agents/flight_agent.py` - lightweight FlightAgent class with a deterministic mock.
- `models.py` - small dataclasses used by the scaffold.
- `static/index.html` - a tiny UI that POSTs to `/a2a/flight` (endpoint stub; not implemented in scaffold).

To run the app with FastAPI/uvicorn (install dependencies first):

```powershell
pip install -r requirements.txt
uvicorn main:create_app --reload
```

The scaffold intentionally avoids importing FastAPI at module import time so `import main` works for quick checks.

## A2A Flight agent (FlightAPI.io integration)

This project includes an A2A-compatible endpoint at `/a2a/flight` that accepts JSON-RPC 2.0 or a simple `{ "query": {...} }` payload.

Environment variables:

- `FLIGHT_PROVIDER` - optional; set to `flightapi` or a provider base URL (defaults to `mock`).
- `FLIGHT_PROVIDER_API_KEY` - your FlightAPI.io API key (required to call the real service).

Example JSON-RPC request:

{
	"jsonrpc": "2.0",
	"id": "flight001",
	"method": "flight/search",
	"params": {
		"destination": "London",
		"date": "2025-11-10"
	}
}

The agent will attempt to detect the caller's origin using `https://ipapi.co/json/` when an origin is not supplied, map cities to IATA codes, call FlightAPI.io's `onewaytrip` endpoint and return a JSON result containing the top flight options.

If no API key is set the agent will return deterministic mock results so the endpoint remains usable for local testing.
