"""AppSail launcher that keeps health diagnostics reachable on import failure."""

import traceback

try:
    from backend.app import app
except Exception as exc:
    from fastapi import FastAPI

    import_error = {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }
    print(f"[FATAL] Drishti application import failed: {import_error['traceback']}")

    app = FastAPI(title="Drishti Startup Diagnostics")

    @app.get("/api/health")
    def failed_health():
        return {
            "status": "error",
            "service": "drishti-intelligence-api",
            "dataLoaded": False,
            "initializationError": import_error,
        }
