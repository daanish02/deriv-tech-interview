"""API server entry point — starts uvicorn with hot-reload.

Run directly:
    uv run python api_main.py

Or via the project script:
    uv run run-api
"""

import uvicorn


def main() -> None:
    """Start the uvicorn server hosting the FastAPI application.

    Hot-reload is enabled so the server restarts automatically when any
    source file inside the project directory changes — intended for
    development use. Disable reload (reload=False) for production deployments.
    """
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
