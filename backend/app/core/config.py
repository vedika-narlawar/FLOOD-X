import os


def cors_origins() -> list[str]:
    return [o.strip() for o in os.environ.get("FLOODX_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]


def rate_limit_per_min() -> int:
    return int(os.environ.get("FLOODX_RATE_LIMIT_PER_MIN", "240"))
