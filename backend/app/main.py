from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .core.config import cors_origins, rate_limit_per_min
from .repositories.artifacts import Unavailable

log = logging.getLogger("floodx.api")
app = FastAPI(title="FLOOD-X API", version="0.1.0",
              description="Urban flood susceptibility screening and exposure for Pune. Outputs are relative screening scores, not flood forecasts.")
app.add_middleware(CORSMiddleware, allow_origins=cors_origins(), allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        ip = request.client.host if request.client else "unknown"
        q, now = _hits[ip], time.time()
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= rate_limit_per_min():
            return JSONResponse({"detail": {"status": "rate_limited", "reason": "Too many requests"}}, status_code=429)
        q.append(now)
    t0 = time.time()
    resp = await call_next(request)
    log.info("%s %s -> %s %.0fms", request.method, request.url.path, resp.status_code, (time.time() - t0) * 1000)
    return resp


@app.exception_handler(Unavailable)
async def unavailable_handler(_: Request, exc: Unavailable):
    return JSONResponse(status_code=503, content={"detail": exc.detail()})


app.include_router(router)

_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
