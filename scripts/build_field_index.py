"""Build a reverse field -> endpoint index from bible + probed responses.

Outputs:
  .planning/field-index.json
    {
      "fieldPath": [
        {
          "endpoint": "/payroll/v1/getPayrollVoucherForBatch",
          "required_params": ["clientId", "batchId"],
          "verified": true,
          "sample_value_masked": "...",
          "cost_hint": "batch_scoped"   # client_scoped | employee_scoped
                                         # | tenant_scoped | batch_scoped
        },
        ...
      ]
    }

  .planning/field-index-summary.md
    Human-readable index of high-value fields (FICA flags, tax withholding,
    YTD wages, classification, addresses, benefits).

Method:
  1. Walk every JSON file under .planning/verified-responses/ (probed).
  2. Flatten each response into dot-paths (list index = '[]').
  3. For each field, record the endpoint path.
  4. Cross-reference the bible (prismhr-methods-full.json) for required
     parameters.
  5. Classify cost_hint by whether the endpoint wants a batchId, clientId
     alone, employeeId, or nothing.
  6. Emit JSON + summary markdown.

Run:
  .venv/Scripts/python scripts/build_field_index.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PROBED = REPO / ".planning" / "verified-responses"
BIBLE = REPO / ".planning" / "prismhr-methods-full.json"
OUT_JSON = REPO / ".planning" / "field-index.json"
OUT_MD = REPO / ".planning" / "field-index-summary.md"


# High-value fields the workflows routinely need. Surfaced in the summary.
PRIORITY_KEYWORDS = (
    "fica", "medicare", "socialSec", "ssnList", "ssn", "oasdi",
    "exempt", "employeeType", "employmentType", "taxWithholding",
    "ytdGross", "ytdWage", "workState", "unionId", "unionCode",
    "hireDate", "terminationDate", "birthDate", "compensationClass",
    "payCode", "deductionCode", "benefitPlan", "empTaxDeductCode",
    "w2", "1095", "1099", "garnishment", "loan",
)

# Endpoints whose params tell us how costly they are.
COST_ORDER = {
    "tenant_scoped":  10,   # no required params
    "client_scoped":   8,   # clientId only
    "employee_scoped": 5,   # clientId + employeeId (narrow)
    "batch_scoped":    3,   # clientId + batchId (very narrow)
    "specific":        1,   # needs a specific id you might not have
}


def flatten(obj, prefix: str = ""):
    """Yield (path, value) tuples for every leaf in a JSON structure.
    Lists become `path[]`; we descend into the first element only so the
    path schema is captured without multiplying per element."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            yield (path, v)
            if isinstance(v, (dict, list)):
                yield from flatten(v, path)
    elif isinstance(obj, list) and obj:
        first = obj[0]
        if isinstance(first, (dict, list)):
            yield from flatten(first, prefix + "[]")
        else:
            yield (prefix + "[]", first)


def endpoint_from_filename(name: str) -> tuple[str, dict]:
    """Return (endpoint_path, extra_params).

    Filenames:
      employee_getEmployeeList.json   -> (/employee/v1/getEmployeeList, {})
      employee_getEmployee_Compensation.json
          -> (/employee/v1/getEmployee, {'options': 'Compensation'})
      system_getData_Employee_Compensation.json
          -> (/system/v1/getData, {'schemaName': 'Employee',
                                   'className': 'Compensation'})
    """
    base = name.replace(".json", "")
    if "_" not in base:
        return f"/{base}", {}
    parts = base.split("_")
    service = parts[0]
    # Multi-part filenames indicate class / options suffixes.
    if service == "system" and len(parts) >= 4 and parts[1] == "getData":
        return "/system/v1/getData", {
            "schemaName": parts[2],
            "className": "_".join(parts[3:]),
        }
    if len(parts) >= 3 and parts[1].startswith("get"):
        # e.g. employee_getEmployee_Compensation = options variant
        return f"/{service}/v1/{parts[1]}", {"options": "_".join(parts[2:])}
    return f"/{service}/v1/{parts[1]}", {}


def classify_cost(required_params: set[str]) -> str:
    if not required_params:
        return "tenant_scoped"
    req = {p.lower() for p in required_params}
    if "batchid" in req:
        return "batch_scoped"
    if "voucherid" in req or "batchids" in req:
        return "specific"
    if "employeeid" in req and "clientid" in req:
        return "employee_scoped"
    if "clientid" in req:
        return "client_scoped"
    return "specific"


def build_bible_index() -> dict[str, dict]:
    """Map endpoint path -> {required_params, summary}."""
    if not BIBLE.exists():
        return {}
    data = json.loads(BIBLE.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for m in (data if isinstance(data, list) else data.get("methods") or []):
        path = m.get("path") or ""
        if not path:
            continue
        required = set()
        for p in m.get("parameters") or []:
            if p.get("required"):
                required.add(p.get("name") or "")
        out[path] = {
            "required_params": sorted(required),
            "summary": m.get("summary") or "",
            "service": m.get("service") or "",
            "operation": m.get("operation") or "",
        }
    return out


def main() -> int:
    bible = build_bible_index()
    print(f"Bible endpoints indexed: {len(bible)}")
    print(f"Probed response files:   {sum(1 for _ in PROBED.glob('*.json'))}")

    index: dict[str, list[dict]] = defaultdict(list)
    per_endpoint_fields: dict[str, set[str]] = defaultdict(set)

    for fp in sorted(PROBED.glob("*.json")):
        try:
            body = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        endpoint, extras = endpoint_from_filename(fp.name)
        bible_entry = bible.get(endpoint, {})
        required = set(bible_entry.get("required_params") or [])
        cost = classify_cost(required)
        # Label with extras so two rows for the same endpoint with
        # different options show up distinctly in the index.
        label = endpoint
        if extras:
            params_str = "&".join(f"{k}={v}" for k, v in extras.items())
            label = f"{endpoint}?{params_str}"

        # Field presence (even null) = schema coverage
        for path, val in flatten(body):
            per_endpoint_fields[label].add(path)
            # Skip boilerplate envelope fields
            if path in {"errorCode", "errorMessage", "extension", "total",
                        "startpage", "count", "infoMessage", "updateMessage"}:
                continue
            # Sample value, masked
            sample = ""
            if isinstance(val, (str, int, float)) and val not in (None, ""):
                s = str(val)
                if len(s) > 24:
                    s = s[:21] + "..."
                sample = s
            entry = {
                "endpoint": label,
                "required_params": sorted(required),
                "verified": True,
                "cost_hint": cost,
                "sample": sample,
                "populated": val not in (None, "", [], {}),
            }
            # Dedupe per field+endpoint; keep the "populated" winner
            existing = next(
                (e for e in index[path] if e["endpoint"] == label), None
            )
            if existing is None:
                index[path].append(entry)
            elif entry["populated"] and not existing["populated"]:
                existing.update(entry)

    # Sort endpoints per field by cost (lower score = more specific & fast)
    for field_path, entries in index.items():
        entries.sort(key=lambda e: COST_ORDER.get(e["cost_hint"], 99))

    # Write JSON
    serializable = {k: v for k, v in sorted(index.items())}
    OUT_JSON.write_text(
        json.dumps(serializable, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"Wrote {OUT_JSON.relative_to(REPO)} ({len(serializable)} field paths)")

    # Write summary markdown — filtered to priority keywords
    md_lines: list[str] = [
        "# PrismHR Field Index — high-value fields",
        "",
        "Generated by `scripts/build_field_index.py`. Shows, for each high-",
        "value field that workflows need, the fastest endpoint to pull it.",
        "",
        "**Cost scale:** `tenant_scoped` > `client_scoped` > `employee_scoped` >",
        "`batch_scoped` > `specific`. Lower == more specific inputs needed,",
        "means fewer bytes transferred but prerequisites to obtain the id.",
        "",
        "Only verified endpoints (probed against UAT) are listed here.",
        "Fields present in the response schema but null in UAT are still",
        "listed (they should populate in prod).",
        "",
    ]
    priority_hits: dict[str, list[dict]] = {
        k: v for k, v in index.items()
        if any(kw.lower() in k.lower() for kw in PRIORITY_KEYWORDS)
    }
    md_lines.append(
        f"Priority fields found: **{len(priority_hits)}** of **{len(index)}** total indexed."
    )
    md_lines.append("")
    for field_path in sorted(priority_hits):
        entries = priority_hits[field_path]
        md_lines.append(f"## `{field_path}`")
        md_lines.append("")
        md_lines.append("| Endpoint | Required | Cost | Populated | Sample |")
        md_lines.append("|---|---|---|---|---|")
        for e in entries:
            req = ", ".join(e["required_params"]) or "—"
            pop = "yes" if e["populated"] else "**EMPTY in UAT**"
            sample = e["sample"] or ""
            md_lines.append(
                f"| `{e['endpoint']}` | {req} | `{e['cost_hint']}` | {pop} | {sample} |"
            )
        md_lines.append("")
    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_MD.relative_to(REPO)}")

    # Endpoint richness summary
    print()
    print("Top 15 endpoints by field count:")
    ranked = sorted(
        per_endpoint_fields.items(), key=lambda kv: -len(kv[1])
    )
    for ep, fields in ranked[:15]:
        print(f"  {len(fields):4d}  {ep}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
