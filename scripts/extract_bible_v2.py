"""Bible extractor v2 — parses inline request schemas.

The PrismHR bible PDF captures each endpoint as a mostly-self-contained block.
For endpoints with a request body, the Request Body section contains a
Python-dict-style serialization of the inline schema, for example:

    Request Body:
    - Content-Type: application/x-www-form-urlencoded
      Schema: {'required': ['clientId', 'employeeId'], 'type': 'object',
      'properties': {'clientId': {'type': 'string', 'description': 'client
      identifier'}, 'employeeId': {'type': 'string', 'description': 'employee
      identifier'}}}

v1 only pulled out the literal `'required': [...]` list via a narrow regex.
v2 parses the whole Python dict with `ast.literal_eval`, flattens any nested
`properties`, and records per-field `type`/`description`/`format`/`enum`
where available.

Also captures inline response schemas where they exist (rare — most responses
use `$ref: '#/components/schemas/...'` with no inline definition in the PDF).

Output: `.planning/prismhr-methods-v2.json` with the full extracted contract.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
from collections import defaultdict
from typing import Any

import pymupdf

PDF_PATH = pathlib.Path(
    r"C:\Users\NiharKulkarni\OneDrive - Simploy, Inc\Desktop\Junk"
    r"\Prism Documentation\prismapi_full_bible_with_index.pdf"
)

OUT_JSON = pathlib.Path(".planning/prismhr-methods-v2.json")
OUT_DIR = pathlib.Path(".planning")
OUT_DIR.mkdir(exist_ok=True)


def split_endpoint_blocks(full_text: str) -> list[str]:
    return re.split(r"(?m)^Endpoint:\s*", full_text)[1:]


def _safe_literal_eval(text: str) -> Any | None:
    """Parse a Python-dict-literal string; return None on failure."""
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None


def _extract_inline_schema(section_text: str) -> dict[str, Any] | None:
    """Find the first `Schema: {...}` block and try to parse it.

    The bible wraps the dict literal across multiple PDF lines with irregular
    indentation. We greedily grab from the opening `{` to the matching `}`
    using a depth counter, then hand to ast.literal_eval.
    """
    idx = section_text.find("Schema:")
    if idx < 0:
        return None
    # Advance past "Schema:" and any whitespace to the first `{` (if inline)
    i = idx + len("Schema:")
    while i < len(section_text) and section_text[i] in " \t\n":
        i += 1
    if i >= len(section_text) or section_text[i] != "{":
        return None  # schema was a $ref or absent
    # Walk braces, respecting quoted strings
    depth = 0
    end = None
    in_single = False
    in_double = False
    for j in range(i, len(section_text)):
        ch = section_text[j]
        if in_single:
            if ch == "'" and section_text[j - 1] != "\\":
                in_single = False
            continue
        if in_double:
            if ch == '"' and section_text[j - 1] != "\\":
                in_double = False
            continue
        if ch == "'":
            in_single = True
            continue
        if ch == '"':
            in_double = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    if end is None:
        return None
    blob = section_text[i:end]
    # Replace PDF soft-wrap artifacts (stray newlines inside strings cause parse fails)
    cleaned = re.sub(r"\n\s*", " ", blob)
    return _safe_literal_eval(cleaned)


def _flatten_properties(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Given a parsed OpenAPI-style schema dict, return [{name, type, description, required, ...}] rows."""
    out: list[dict[str, Any]] = []
    if not isinstance(schema, dict):
        return out
    required = set(schema.get("required") or [])
    props = schema.get("properties") or {}
    if not isinstance(props, dict):
        return out
    for name, spec in props.items():
        if not isinstance(spec, dict):
            out.append({"name": name, "type": "unknown", "required": name in required})
            continue
        row: dict[str, Any] = {
            "name": name,
            "type": spec.get("type"),
            "description": spec.get("description"),
            "format": spec.get("format"),
            "enum": spec.get("enum"),
            "required": name in required,
        }
        # Nested items for array types
        if spec.get("type") == "array" and isinstance(spec.get("items"), dict):
            item = spec["items"]
            row["item_type"] = item.get("type")
            if item.get("type") == "object" and isinstance(item.get("properties"), dict):
                row["item_properties"] = _flatten_properties(item)
            elif "$ref" in item:
                row["item_ref"] = item["$ref"]
        # Nested object schema
        if spec.get("type") == "object" and "properties" in spec:
            row["object_properties"] = _flatten_properties(spec)
        if "$ref" in spec:
            row["ref"] = spec["$ref"]
        # Drop None values for compactness
        row = {k: v for k, v in row.items() if v is not None}
        out.append(row)
    return out


def parse_endpoint_block(block: str) -> dict[str, Any] | None:
    path_match = re.match(r"(\S+)", block)
    method_match = re.search(r"(?m)^Method:\s*(\S+)", block)
    if not (path_match and method_match):
        return None

    path = path_match.group(1)
    method = method_match.group(1)
    summary_match = re.search(r"(?m)^Summary:\s*(.+)", block)
    summary = summary_match.group(1).strip() if summary_match else ""

    desc_match = re.search(
        r"Description:\s*(.+?)(?=\n(?:Parameters:|Request Body:|Responses:))",
        block,
        flags=re.DOTALL,
    )
    description = re.sub(r"\s+", " ", desc_match.group(1)).strip() if desc_match else ""

    # ----- Parameters -----
    params: list[dict[str, Any]] = []
    params_section = re.search(
        r"Parameters:\s*(.+?)(?=\n(?:Request Body:|Responses:)|\Z)",
        block,
        flags=re.DOTALL,
    )
    if params_section:
        pt = params_section.group(1)
        for pmatch in re.finditer(
            r"-\s+(\S+)\s+\(in:\s+(\w+),\s+required:\s+(\w+)\)(.*?)(?=\n-\s+\S+\s+\(in:|\Z)",
            pt,
            flags=re.DOTALL,
        ):
            name, loc, req, tail = pmatch.group(1), pmatch.group(2), pmatch.group(3), pmatch.group(4)
            desc_m = re.search(r"Description:\s*(.+?)(?:\n\s*-|\Z)", tail, flags=re.DOTALL)
            params.append(
                {
                    "name": name,
                    "location": loc,
                    "required": req.lower() == "true",
                    "description": re.sub(r"\s+", " ", desc_m.group(1)).strip() if desc_m else "",
                }
            )

    # ----- Request body -----
    request_body: dict[str, Any] | None = None
    rb_section = re.search(r"Request Body:\s*(.+?)(?=\nResponses:|\Z)", block, flags=re.DOTALL)
    if rb_section:
        rb_text = rb_section.group(1)
        content_types = list(set(re.findall(r"Content-Type:\s*(\S+)", rb_text)))
        schema_refs = list(set(re.findall(r"#/components/schemas/(\w+)", rb_text)))
        inline_schema = _extract_inline_schema(rb_text)
        fields: list[dict[str, Any]] = []
        required: list[str] = []
        if inline_schema:
            fields = _flatten_properties(inline_schema)
            required = list(inline_schema.get("required") or [])
        # Only flag inline-present when the schema has real fields or
        # type info — not when it's a bare `{'$ref': ...}` with nothing else.
        real_inline = bool(
            inline_schema
            and (
                inline_schema.get("properties")
                or inline_schema.get("type")
                or inline_schema.get("required")
            )
        )
        request_body = {
            "content_types": content_types,
            "schema_refs": schema_refs,
            "required_fields": required,
            "fields": fields,
            "inline_schema_present": real_inline,
        }

    # ----- Responses -----
    responses: dict[str, dict[str, Any]] = {}
    resp_section = re.search(r"Responses:\s*(.+?)\Z", block, flags=re.DOTALL)
    if resp_section:
        rt = resp_section.group(1)
        for rmatch in re.finditer(
            r"- (\d{3}):\s*(.+?)(?=\n- \d{3}:|\Z)", rt, flags=re.DOTALL
        ):
            status = rmatch.group(1)
            body = rmatch.group(2)
            content_types = list(set(re.findall(r"Content-Type:\s*(\S+)", body)))
            schema_refs = list(set(re.findall(r"#/components/schemas/(\w+)", body)))
            inline_schema = _extract_inline_schema(body)
            real_resp_inline = bool(
                inline_schema
                and (
                    inline_schema.get("properties")
                    or (inline_schema.get("type") and inline_schema.get("type") != "object")
                )
            )
            first_line = body.strip().split("\n")[0].strip()
            responses[status] = {
                "description": first_line[:200],
                "content_types": content_types,
                "schema_refs": schema_refs,
                "inline_schema_present": real_resp_inline,
                "fields": _flatten_properties(inline_schema) if real_resp_inline else [],
            }

    parts = path.strip("/").split("/")
    return {
        "path": path,
        "method": method,
        "service": parts[0] if parts else "",
        "version": parts[1] if len(parts) > 1 else "",
        "operation": parts[2] if len(parts) > 2 else "",
        "summary": summary,
        "description": description,
        "parameters": params,
        "request_body": request_body,
        "responses": responses,
        # Derived verification flags
        "request_verified": bool(
            request_body and request_body.get("inline_schema_present")
            and request_body.get("fields")
        ) or method == "GET" and all(p["name"] for p in params),
        "response_verified": any(
            r.get("inline_schema_present") for r in responses.values()
        ),
    }


def main() -> None:
    doc = pymupdf.open(PDF_PATH)
    full = "\n".join(doc[p].get_text() for p in range(doc.page_count))

    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for b in split_endpoint_blocks(full):
        rec = parse_endpoint_block(b)
        if not rec:
            continue
        key = (rec["path"], rec["method"])
        if key in seen:
            continue
        seen.add(key)
        records.append(rec)

    OUT_JSON.write_text(json.dumps(records, indent=2), encoding="utf-8")

    # ----- Print verification coverage -----
    by_svc: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_svc[r["service"]].append(r)

    total = len(records)
    body_endpoints = sum(1 for r in records if r["request_body"])
    body_with_inline = sum(
        1 for r in records if r["request_body"] and r["request_body"]["inline_schema_present"]
    )
    body_fields_captured = sum(
        len((r["request_body"] or {}).get("fields") or []) for r in records
    )
    resp_with_inline = sum(
        1 for r in records if any(
            s.get("inline_schema_present") for s in r["responses"].values()
        )
    )

    print(f"total endpoints: {total}")
    print(f"endpoints with request body: {body_endpoints}")
    print(f"  of those, inline schema parsed: {body_with_inline}")
    print(f"  total request-body fields captured: {body_fields_captured}")
    print(f"endpoints with any inline response schema: {resp_with_inline}")
    print()
    print("Per-service coverage:")
    for svc, items in sorted(by_svc.items(), key=lambda kv: -len(kv[1])):
        bodies = sum(1 for r in items if r["request_body"])
        inline = sum(
            1 for r in items
            if r["request_body"] and r["request_body"]["inline_schema_present"]
        )
        print(f"  {svc:20s} {len(items):4d} endpoints  bodies={bodies:3d}  inline-parsed={inline:3d}")


if __name__ == "__main__":
    main()
