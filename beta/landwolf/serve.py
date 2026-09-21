"""Single-worker production entry point with explicit resource bounds."""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT is outside the allowed range")
    uvicorn.run(
        "landwolf.main:create_app",
        factory=True,
        host=os.environ.get("LANDWOLF_BIND_HOST", "127.0.0.1"),
        port=port,
        workers=1,
        limit_concurrency=32,
        timeout_keep_alive=5,
        timeout_graceful_shutdown=20,
        proxy_headers=False,
        access_log=False,
    )
