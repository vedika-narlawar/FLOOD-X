"""Shared infrastructure: paths, logging, atomic IO, resilient downloads, provenance."""
from __future__ import annotations
from urllib.parse import urlparse

import datetime as dt
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    """Minimal .env loader (stdlib only); real environment variables take precedence."""
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def data_dir() -> Path:
    return Path(os.environ.get("FLOODX_DATA_DIR", ROOT / "data")).resolve()


def art_dir() -> Path:
    return Path(os.environ.get("FLOODX_ARTIFACTS_DIR", ROOT / "artifacts")).resolve()


def config_dir() -> Path:
    return Path(os.environ.get("FLOODX_CONFIG_DIR", ROOT / "configs")).resolve()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def get_logger(name: str = "floodx") -> logging.Logger:
    log = logging.getLogger(name)
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    log.addHandler(sh)
    try:
        (art_dir() / "logs").mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(art_dir() / "logs" / "pipeline.log")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except OSError:
        pass
    return log


def write_json_atomic(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str, allow_nan=False))
    os.replace(tmp, path)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return default


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


class SourceUnavailable(Exception):
    """A remote source cannot be reached (network/DNS/HTTP). Stage becomes 'blocked'."""


class Blocked(Exception):
    """A stage cannot run because required inputs are missing. Carries a human reason."""

    def __init__(self, reason: str, missing: list[str] | None = None):
        super().__init__(reason)
        self.reason = reason
        self.missing = missing or []


class DownloadError(SourceUnavailable):
    pass


def user_agent() -> str:
    contact = os.environ.get("FLOODX_CONTACT", "unset")
    return f"FLOOD-X/0.1 (academic project; contact: {contact})"


def _is_dns_error(exc: BaseException) -> bool:
    """Return True when an exception or its causes indicate DNS resolution failure."""
    seen = set()
    pending = [exc]

    dns_terms = (
        "nameresolutionerror",
        "name or service not known",
        "getaddrinfo failed",
        "failed to resolve",
        "temporary failure in name resolution",
        "nodename nor servname provided",
    )

    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))

        if any(term in repr(current).lower() for term in dns_terms):
            return True

        if current.__cause__ is not None:
            pending.append(current.__cause__)
        if current.__context__ is not None:
            pending.append(current.__context__)

        for arg in current.args:
            if isinstance(arg, BaseException):
                pending.append(arg)

    return False

def request_with_retry(method: str, url: str, *, retries: int = 4, backoff: float = 1.5,
                       timeout: float = 60, session: requests.Session | None = None, **kw) -> requests.Response:
    """Bounded exponential backoff. 4xx (except 429) is not retried."""
    hostname = urlparse(url).hostname
    if hostname and hostname.lower().endswith(".invalid"):
    	raise DownloadError(
        	f"DNS resolution failed for {url} "
        	"(reserved .invalid domain)"
    )
    s = session or requests
    headers = {"User-Agent": user_agent(), **kw.pop("headers", {})}
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = s.request(method, url, timeout=timeout, headers=headers, **kw)
            if r.status_code == 429 or r.status_code >= 500:
                last = DownloadError(f"HTTP {r.status_code} from {url}")
                delay = float(r.headers.get("Retry-After", backoff ** attempt)) if r.status_code == 429 else backoff ** attempt
                time.sleep(min(delay, 30))
                continue
            return r
        
        except requests.RequestException as e:
            last = e
            error_text = repr(e).lower()

            if _is_dns_error(e):
                raise DownloadError(
                    f"DNS resolution failed for {url} "
                    "(host unreachable from this environment)"
                ) from e

            time.sleep(min(backoff ** attempt, 30))
    raise DownloadError(f"{method} {url} failed after {retries} attempts: {last}")


def download_file(url: str, dest: Path, *, min_bytes: int = 1, retries: int = 4, timeout: float = 120,
                  force: bool = False, session: requests.Session | None = None) -> dict:
    """Streaming, integrity-checked, atomic download. A valid existing file is never
    overwritten by a failed/truncated transfer; idempotent unless force=True."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_bytes and not force:
        return {"url": url, "path": str(dest), "bytes": dest.stat().st_size, "sha256": sha256_file(dest),
                "retrieved_at": None, "skipped_existing": True}
    part = dest.with_suffix(dest.suffix + ".part")
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with request_with_retry("GET", url, retries=1, timeout=timeout, stream=True, session=session) as r:
                if r.status_code != 200:
                    raise DownloadError(f"HTTP {r.status_code} for {url}")
                expected = r.headers.get("Content-Length")
                n = 0
                with open(part, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                        n += len(chunk)
                # Content-Length counts *transferred* (possibly gzip-compressed) bytes, so compare against
                # the raw socket byte count, not the decoded size.
                try:
                    transferred = r.raw.tell()
                except Exception:
                    transferred = n
                if r.headers.get("Content-Encoding") and transferred == 0:
                    transferred = None  # cannot verify through a transparent decoder
            if expected is not None and transferred is not None and int(expected) != transferred:
                raise DownloadError(f"truncated download: got {transferred} of {expected} bytes")
            if n < min_bytes:
                raise DownloadError(f"file too small ({n} bytes < {min_bytes})")
            os.replace(part, dest)
            return {"url": url, "path": str(dest), "bytes": n, "sha256": sha256_file(dest),
                    "retrieved_at": now_iso(), "skipped_existing": False}
        except (DownloadError, requests.RequestException) as e:
            last = e
            part.unlink(missing_ok=True)
            if _is_dns_error(e) or "DNS resolution failed" in str(e).lower():
                break
            time.sleep(min(1.5 ** attempt, 20))
    raise DownloadError(f"download failed for {url}: {last}")
