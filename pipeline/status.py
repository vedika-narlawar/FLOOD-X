"""Pipeline stage status ledger: records only what actually executed."""
from __future__ import annotations

from .common import art_dir, now_iso, read_json, write_json_atomic

VALID = {"pending", "success", "blocked", "failed", "skipped"}


def path():
    return art_dir() / "pipeline_status.json"


def load() -> dict:
    return read_json(path(), {"stages": {}, "history": []})


def record(stage: str, status: str, message: str = "", outputs: list[str] | None = None,
           started: str | None = None, details: dict | None = None) -> None:
    assert status in VALID, status
    led = load()
    entry = {"status": status, "message": message, "outputs": outputs or [], "started_at": started,
             "finished_at": now_iso(), "details": details or {}}
    led["stages"][stage] = entry
    led["history"].append({"stage": stage, **{k: entry[k] for k in ("status", "message", "started_at", "finished_at")}})
    led["history"] = led["history"][-500:]
    write_json_atomic(path(), led)
