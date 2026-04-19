"""Probe every authorized GET method against PrismHR UAT and record response shapes.

Goal: ground the Pydantic models in real data, not guessed bible syntax. For
each method this script can hit, writes a sample response to
`.planning/probe-responses/<service>_<op>.json` plus a probe log to
`.planning/probe-summary.json` (status, required params inferred from
400 errors, response shape, timing).

Skips obvious file-download methods (no value probing, may be large).
Uses the same session + client + secure_env as the dogfood script.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import SessionManager
from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.config import Settings
from prismhr_mcp.secure_env import load_into_environ

# Heuristic skip list — methods whose names suggest a file download or a
# mutation disguised as GET. We skip these until per-method metadata lands.
SKIP_NAME_MARKERS = (
    "download",
    "export",
    "print",
)

# Per-endpoint scrub — some PrismHR responses echo operator contact strings
# that can include credential material at UAT (the `contactInfo` field under
# `getAPIPermissions` is a known offender). Don't save those to disk where
# they might slip into a commit. The probe-summary.json only records status
# + shape, not body, so it is safe.
SKIP_SAVE_PATHS = {"/login/v1/getAPIPermissions"}


def _shape(value: Any, depth: int = 0) -> Any:
    """Return a skeleton of the JSON response showing keys + types only."""
    if depth > 4:
        return "..."
    if isinstance(value, dict):
        return {k: _shape(v, depth + 1) for k, v in list(value.items())[:25]}
    if isinstance(value, list):
        if not value:
            return []
        return [_shape(value[0], depth + 1), f"+{len(value)-1} more" if len(value) > 1 else None]
    return type(value).__name__


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    settings = Settings()
    http = httpx.AsyncClient(timeout=30.0)
    creds = DirectCredentialSource(
        settings.prismhr_peo_id,
        __import__("os").environ["PRISMHR_MCP_USERNAME"],
        __import__("os").environ["PRISMHR_MCP_PASSWORD"],
    )
    session = SessionManager(settings, creds, http)
    client = PrismHRClient(settings, session, http)

    methods = json.loads(pathlib.Path(".planning/prismhr-methods.json").read_text())
    gets = [m for m in methods if m["method"] == "GET" and m["service"] in {"payroll", "timesheet", "system", "login"}]

    responses_dir = pathlib.Path(".planning/probe-responses")
    responses_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, Any]] = []
    print(f"Probing {len(gets)} authorized GETs...\n", flush=True)

    for i, meth in enumerate(gets, 1):
        path = meth["path"]
        op = meth["operation"]
        skip = any(marker in op.lower() for marker in SKIP_NAME_MARKERS)
        if skip:
            print(f"[{i:2d}/{len(gets)}] SKIP    {path}  (download-like)", flush=True)
            summary.append({"path": path, "status": "skipped", "reason": "download-like"})
            continue

        start = time.monotonic()
        try:
            raw = await client.get(path)
            status = 200
            err = None
        except Exception as exc:  # noqa: BLE001
            raw = None
            status = None
            err = str(exc)[:500]
        elapsed_ms = int((time.monotonic() - start) * 1000)

        record: dict[str, Any] = {
            "path": path,
            "service": meth["service"],
            "operation": op,
            "summary": meth["summary"],
            "elapsed_ms": elapsed_ms,
        }

        if err:
            record["status"] = "error"
            record["error"] = err
            print(f"[{i:2d}/{len(gets)}] ERR     {path:60s} ({elapsed_ms}ms) {err[:80]}", flush=True)
        else:
            record["status"] = "ok"
            record["http"] = status
            record["shape"] = _shape(raw)
            # Save full response (truncate giant lists) unless flagged to
            # skip (responses that can leak credential-adjacent data).
            if path not in SKIP_SAVE_PATHS:
                out_path = responses_dir / f"{meth['service']}_{op}.json"
                try:
                    out_path.write_text(
                        json.dumps(raw, indent=2, default=str)[:80000],
                        encoding="utf-8",
                    )
                except Exception:
                    pass
            # Detect errorCode in response body
            if isinstance(raw, dict):
                err_code = raw.get("errorCode")
                err_msg = raw.get("errorMessage")
                if err_code not in (None, "", "0"):
                    record["status"] = "error"
                    record["prismhr_error_code"] = err_code
                    record["prismhr_error_message"] = err_msg
                    print(f"[{i:2d}/{len(gets)}] PHR ERR {path:60s} ({elapsed_ms}ms) [{err_code}] {err_msg[:60]}", flush=True)
                else:
                    print(f"[{i:2d}/{len(gets)}] OK      {path:60s} ({elapsed_ms}ms)", flush=True)
            else:
                print(f"[{i:2d}/{len(gets)}] OK      {path:60s} ({elapsed_ms}ms)", flush=True)

        summary.append(record)

    pathlib.Path(".planning/probe-summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    ok_count = sum(1 for r in summary if r.get("status") == "ok")
    err_count = sum(1 for r in summary if r.get("status") == "error")
    skip_count = sum(1 for r in summary if r.get("status") == "skipped")
    print(f"\nDone. OK={ok_count}, ERR={err_count}, SKIP={skip_count}")
    print(f"Summary: .planning/probe-summary.json")
    print(f"Per-method samples: .planning/probe-responses/")

    await http.aclose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
