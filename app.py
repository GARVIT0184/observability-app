import time
import uuid
import collections
import threading

from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse, JSONResponse

app = FastAPI()

START_TIME = time.time()

# --- Live, thread-safe counter -------------------------------------------------
_lock = threading.Lock()
REQUEST_COUNT = 0

def bump_counter():
    global REQUEST_COUNT
    with _lock:
        REQUEST_COUNT += 1
        return REQUEST_COUNT

# --- In-memory structured log buffer -------------------------------------------
LOG_BUFFER = collections.deque(maxlen=2000)

def add_log(level: str, path: str, request_id: str, **extra):
    entry = {
        "level": level,
        "ts": time.time(),
        "path": path,
        "request_id": request_id,
    }
    entry.update(extra)
    LOG_BUFFER.append(entry)


# --- Middleware: runs for every request to every endpoint ----------------------
@app.middleware("http")
async def instrument_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    bump_counter()  # counter increases on every request, to any endpoint

    try:
        response = await call_next(request)
        add_log(
            "info",
            request.url.path,
            request_id,
            method=request.method,
            status_code=response.status_code,
        )
        return response
    except Exception as exc:
        add_log(
            "error",
            request.url.path,
            request_id,
            method=request.method,
            error=str(exc),
        )
        raise


# --- Endpoints -------------------------------------------------------------

@app.get("/work")
def work(n: int = Query(1, ge=0, description="Units of work to perform")):
    """Do K units of 'work' and return the result."""
    total = 0
    for i in range(n):
        total += i * i  # trivial CPU work
    return {"email": "24f2006741@ds.study.iitm.ac.in", "done": n}


@app.get("/metrics")
def metrics():
    """Expose Prometheus text-format metrics, including a live counter."""
    body = (
        "# HELP http_requests_total Total number of HTTP requests received\n"
        "# TYPE http_requests_total counter\n"
        f"http_requests_total {REQUEST_COUNT}\n"
    )
    return PlainTextResponse(content=body, media_type="text/plain; version=0.0.4")


@app.get("/healthz")
def healthz():
    """Basic liveness/health check."""
    uptime = time.time() - START_TIME
    return {"status": "ok", "uptime_s": max(0.0, uptime)}


@app.get("/logs/tail")
def logs_tail(limit: int = Query(10, ge=1, le=2000)):
    """Return the last `limit` structured log entries."""
    snapshot = list(LOG_BUFFER)
    return JSONResponse(content=snapshot[-limit:])


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
