"""Minimal FastAPI scaffold for the Flight Agent project.

This module is safe to import for quick checks (it does not import FastAPI at top-level).
Call create_app() to get a FastAPI app object when FastAPI is installed.
"""

__version__ = "0.1.0"


def create_app():
    """Create and return a FastAPI app instance.

    This function imports FastAPI only when called so importing this module
    doesn't require FastAPI to be installed (useful for quick import checks).
    """
    try:
        from fastapi import FastAPI, Request
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import JSONResponse
    except Exception as e:
        raise RuntimeError("FastAPI is required to create the web app: " + str(e))

    app = FastAPI(title="Flight Agent")

    # instantiate a single agent for the app lifecycle
    try:
        import os
        from agents import FlightAgent
        provider = os.getenv("FLIGHT_PROVIDER", "mock")
        provider_url = os.getenv("FLIGHT_PROVIDER_URL", "")
        api_key = os.getenv("FLIGHT_PROVIDER_API_KEY", "")
        # prefer an explicit provider URL if given
        agent_provider = provider_url if provider_url else provider
        flight_agent = FlightAgent(provider=agent_provider, provider_api_key=api_key)
    except Exception:
        # if agents package isn't present the endpoint will return an error
        flight_agent = None

    # Mount a simple static UI if available
    try:
        app.mount("/ui", StaticFiles(directory="static", html=True), name="static")
    except Exception:
        # ignore if static folder doesn't exist yet
        pass

    @app.post("/a2a/flight")
    async def a2a_flight(request: Request):
        """Simple HTTP endpoint that accepts a JSON payload and returns the cheapest flight.

        Expected request shape (from the scaffold UI):
        { "query": { "from":..., "to":..., "date":..., "adults": N } }
        """
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "invalid json"})

        # support either {query: {...}} or a raw dict
        if isinstance(body, dict) and "query" in body:
            query = body["query"]
        else:
            query = body

        if flight_agent is None:
            return JSONResponse(status_code=500, content={"error": "agent not available"})

        try:
            # agent.process_messages expects a dict with a 'query' key in the scaffold
            result = flight_agent.process_messages({"query": query})
            return JSONResponse(status_code=200, content=result)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    @app.get("/health")
    def _health():
        return {"status": "healthy", "version": __version__}

    return app


if __name__ == "__main__":
    # runtime run if uvicorn is available
    try:
        import uvicorn
        uvicorn.run("main:create_app()", host="127.0.0.1", port=8000, reload=False)
    except Exception as e:
        print("Run with: uvicorn main:create_app --reload")
        print("Error starting uvicorn:", e)


# Many deployment platforms (including Vercel) expect a top-level ASGI `app`
# variable. Provide one by trying to instantiate the FastAPI app. If FastAPI
# (or other dependencies) are not available in the environment, fall back to a
# minimal ASGI app that returns 503 so the import doesn't fail.
try:
    app = create_app()
except Exception:
    async def app(scope, receive, send):
        # minimal ASGI fallback returning 503 for HTTP requests
        if scope.get("type") == "http":
            body = b"FastAPI not available; please install dependencies or run with uvicorn create_app()."
            await send({"type": "http.response.start", "status": 503, "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
            await send({"type": "http.response.body", "body": body})
        else:
            # noop for non-http scopes
            return

# Export `handler` as an alias to the ASGI app so both `app` and `handler` are available
# (some serverless platforms look for `handler` specifically).
try:
    # If Mangum is available, wrap the ASGI app into a Lambda-style handler which
    # works well on many serverless platforms (including Vercel's Python runtime).
    from mangum import Mangum
    handler = Mangum(app)
except Exception:
    # fall back to exporting the ASGI app directly
    handler = app
