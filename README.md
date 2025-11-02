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
