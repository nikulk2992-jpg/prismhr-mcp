"""Sanitize the verification matrix for public commit.

Input:  .planning/verification-matrix.json (contains real UAT IDs)
Output: .planning/verification-matrix-public.json (schema + counts only)

The OSS core reads the public file at runtime to answer `meta_capabilities`
("which endpoints have verified response shapes?") without exposing any
tenant data. Every customer probes locally to populate their own private
matrix; only the schema contribution (which keys the response contains)
flows upstream if they choose to contribute.
"""

from __future__ import annotations

import json
import pathlib
from collections import Counter


def main() -> None:
    src = pathlib.Path(".planning/verification-matrix.json")
    dst = pathlib.Path(".planning/verification-matrix-public.json")
    raw = json.loads(src.read_text(encoding="utf-8"))

    public_probes: list[dict] = []
    for p in raw.get("probes", []):
        public = {
            "path": p["path"],
            "status": p["status"],
        }
        # Schema hints: response keys are fine (they're structural, not data).
        if p.get("response_keys"):
            public["response_keys"] = p["response_keys"]
        # PrismHR error code/message is structural too.
        if p.get("errorCode"):
            public["prismhr_error_code"] = p["errorCode"]
        if p.get("errorMessage"):
            public["prismhr_error_message"] = p["errorMessage"]
        # Explicitly DROP args_used, elapsed_ms, fields_discovered counts
        # (elapsed_ms could be kept; skip for paranoia).
        public_probes.append(public)

    # For fixtures, publish only the key names + size bucket (not values).
    def bucket(n: int) -> str:
        if n == 0:
            return "0"
        if n == 1:
            return "1"
        if n <= 10:
            return "2-10"
        if n <= 100:
            return "11-100"
        if n <= 1000:
            return "101-1000"
        return "1000+"

    fixture_counts = {k: bucket(len(v)) for k, v in raw.get("fixtures", {}).items()}

    out = {
        "note": (
            "Public verification matrix for prismhr-mcp. Contains endpoint "
            "coverage status and response-key schema hints only. No tenant "
            "data (client IDs, employee IDs, payroll detail). Run "
            "`scripts/calibrated_probe.py` against your own PrismHR instance "
            "to build a private matrix with real response bodies in "
            ".planning/verified-responses/ (gitignored)."
        ),
        "authorized_services_note": (
            "The upstream authorized-service list is tenant-specific and "
            "omitted from the public matrix. Use the `meta_upstream_permissions` "
            "tool to see yours."
        ),
        "fixture_key_coverage": fixture_counts,
        "probes": public_probes,
        "summary": {
            "verified": sum(1 for p in public_probes if p["status"] == "verified"),
            "prismhr_error": sum(1 for p in public_probes if p["status"] == "prismhr_error"),
            "transport_error": sum(
                1 for p in public_probes if p["status"] in ("error", "transport_error")
            ),
            "total": len(public_probes),
        },
    }
    dst.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {dst}  ({len(public_probes)} probes, {dst.stat().st_size} bytes)")
    print(f"verified: {out['summary']['verified']}  "
          f"prismhr-err: {out['summary']['prismhr_error']}  "
          f"transport-err: {out['summary']['transport_error']}")


if __name__ == "__main__":
    main()
