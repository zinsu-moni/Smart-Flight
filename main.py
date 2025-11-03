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
        # If the caller uses JSON-RPC (A2A) format, unwrap it and return JSON-RPC
        try:
            # JSON-RPC 2.0 wrapper
            if isinstance(body, dict) and body.get("jsonrpc") == "2.0":
                rpc_id = body.get("id")
                method = body.get("method")

                # extract messages depending on method
                params = body.get("params") or {}
                # default: try to find a message.parts[].data or a params.message
                msg_obj = None
                if method == "message/send":
                    msg_obj = params.get("message")
                elif method == "execute":
                    msg_obj = params.get("messages")

                # normalize parts list
                parts = []
                if isinstance(msg_obj, dict) and "parts" in msg_obj:
                    parts = msg_obj.get("parts") or []
                elif isinstance(msg_obj, list):
                    # 'messages' could be a list of messages
                    for m in msg_obj:
                        if isinstance(m, dict) and "parts" in m:
                            parts.extend(m.get("parts") or [])

                # find the first data part and build a query
                query = None
                for p in parts:
                    if not isinstance(p, dict):
                        continue
                    if p.get("kind") == "data":
                        data = p.get("data") or {}
                        # if data already contains a structured query, use it
                        if isinstance(data, dict) and ("from" in data or "input" in data or "to" in data):
                            query = data
                            break

                # fallback: if params contains direct fields
                if query is None and isinstance(params, dict):
                    if "query" in params and isinstance(params.get("query"), dict):
                        query = params.get("query")
                    else:
                        # accept flat fields like input, from, to
                        # accept both 'to' and 'destination' so callers using that key are supported
                        flat_keys = ("input", "from", "to", "destination", "date", "adults", "flight")
                        q = {k: params.get(k) for k in flat_keys if k in params}
                        if q:
                            query = q

                # if still no query, set to empty dict
                if query is None:
                    query = {}

                if flight_agent is None:
                    resp = {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32000, "message": "agent not available"}}
                    return JSONResponse(status_code=500, content=resp)

                # call the agent with a consistent shape
                try:
                    result = flight_agent.process_messages({"query": query})
                    rpc_resp = {"jsonrpc": "2.0", "id": rpc_id, "result": result}
                    return JSONResponse(status_code=200, content=rpc_resp)
                except Exception as e:
                    rpc_err = {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32603, "message": "Internal error", "data": str(e)}}
                    return JSONResponse(status_code=500, content=rpc_err)

            # support either {query: {...}} or a raw dict (non-RPC callers)
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
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": "unexpected server error", "details": str(e)})

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
