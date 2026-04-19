"""Full PrismHR bible extractor.

Produces three structured outputs under .planning/:

1. prismhr-methods-full.json
   For every endpoint, capture:
     - path, method, service, version, operation, summary, description
     - parameters[]: name, location (header/query/path), required, description
     - request_body: content_type, schema_ref (if any)
     - responses: {status_code: {content_type, schema_ref}}

2. prismhr-schemas.json
   Best-effort parse of `#/components/schemas/*` definitions. Bible is a
   flattened OpenAPI export, so this is heuristic — captures what we can.

3. .planning/map/<service>.md
   Obsidian-compatible per-service markdown with wiki-links between
   related methods. Each method page shows: summary, params, request body,
   response refs, and a "See also" section linking sibling methods.

Run after methods JSON exists (or standalone — it reads the PDF directly).
"""

from __future__ import annotations

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

OUT_DIR = pathlib.Path(".planning")
MAP_DIR = OUT_DIR / "map"
OUT_DIR.mkdir(exist_ok=True)
MAP_DIR.mkdir(parents=True, exist_ok=True)


# ---- Endpoint block parser --------------------------------------------------


def split_endpoint_blocks(full_text: str) -> list[str]:
    """Split text into per-endpoint blocks."""
    return re.split(r"(?m)^Endpoint:\s*", full_text)[1:]


def parse_endpoint_block(block: str) -> dict[str, Any] | None:
    path_match = re.match(r"(\S+)", block)
    method_match = re.search(r"(?m)^Method:\s*(\S+)", block)
    if not (path_match and method_match):
        return None
    path = path_match.group(1)
    method = method_match.group(1)

    # Summary (one line after Summary:)
    summary_match = re.search(r"(?m)^Summary:\s*(.+)", block)
    summary = summary_match.group(1).strip() if summary_match else ""

    # Description is multi-line — between Description: and (Parameters | Request Body | Responses)
    desc_match = re.search(
        r"Description:\s*(.+?)(?=\n(?:Parameters:|Request Body:|Responses:))",
        block,
        flags=re.DOTALL,
    )
    description = (
        re.sub(r"\s+", " ", desc_match.group(1)).strip() if desc_match else ""
    )

    # Parameters section
    params: list[dict[str, str]] = []
    params_section = re.search(
        r"Parameters:\s*(.+?)(?=\n(?:Request Body:|Responses:)|\Z)",
        block,
        flags=re.DOTALL,
    )
    if params_section:
        params_text = params_section.group(1)
        # Each parameter starts with "- " then "(in: LOC, required: BOOL)"
        for pmatch in re.finditer(
            r"- (\S+) \(in: (\w+), required: (\w+)\)\s*(?:\n\s*Description:\s*(.+?))?(?=\n-|\n\s*\n|\Z)",
            params_text,
            flags=re.DOTALL,
        ):
            params.append(
                {
                    "name": pmatch.group(1),
                    "location": pmatch.group(2),
                    "required": pmatch.group(3).lower() == "true",
                    "description": (
                        re.sub(r"\s+", " ", pmatch.group(4)).strip()
                        if pmatch.group(4)
                        else ""
                    ),
                }
            )

    # Request Body — typically has Content-Type + schema $ref
    request_body: dict[str, Any] | None = None
    rb_section = re.search(
        r"Request Body:\s*(.+?)(?=\nResponses:|\Z)", block, flags=re.DOTALL
    )
    if rb_section:
        rb_text = rb_section.group(1)
        content_types = re.findall(r"Content-Type:\s*(\S+)", rb_text)
        schema_refs = re.findall(r"#/components/schemas/(\w+)", rb_text)
        required_fields = re.findall(r"'required':\s*\[([^\]]+)\]", rb_text)
        required_list: list[str] = []
        if required_fields:
            required_list = [
                x.strip().strip("'\"")
                for x in required_fields[0].split(",")
                if x.strip()
            ]
        request_body = {
            "content_types": list(set(content_types)),
            "schema_refs": list(set(schema_refs)),
            "required_fields": required_list,
        }

    # Responses — per-status content-type + schema ref
    responses: dict[str, dict[str, Any]] = {}
    resp_section = re.search(r"Responses:\s*(.+?)\Z", block, flags=re.DOTALL)
    if resp_section:
        resp_text = resp_section.group(1)
        # Split by "- NNN:"
        for rmatch in re.finditer(
            r"- (\d{3}):\s*(.+?)(?=\n- \d{3}:|\Z)", resp_text, flags=re.DOTALL
        ):
            status = rmatch.group(1)
            body = rmatch.group(2)
            content_types = re.findall(r"Content-Type:\s*(\S+)", body)
            schema_refs = re.findall(r"#/components/schemas/(\w+)", body)
            # Grab the first line of the response description
            first_line = body.strip().split("\n")[0].strip()
            responses[status] = {
                "description": first_line[:200],
                "content_types": list(set(content_types)),
                "schema_refs": list(set(schema_refs)),
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
    }


# ---- Schema extractor -------------------------------------------------------


def extract_schemas(full_text: str) -> dict[str, str]:
    """Best-effort schema block capture. Returns name -> raw block text.

    The bible flattens OpenAPI components and intersperses them with
    endpoint specs. We look for `#/components/schemas/<Name>` refs and
    record them, then try to find the schema definitions for those names.
    """
    refs = set(re.findall(r"#/components/schemas/(\w+)", full_text))
    # Attempt to find sections that look like schema bodies. Heuristic:
    # look for `<SchemaName> { 'properties':` or `schema: { ... }`.
    schemas: dict[str, str] = {}
    for name in refs:
        # Try to find the definition block
        m = re.search(
            rf"\b{name}\b\s*[:{{(]\s*[\s\S]{{0,4000}}?(?=\n\s*\n|\Z)",
            full_text,
        )
        if m:
            schemas[name] = m.group(0)[:4000]
    return schemas


# ---- Map writer -------------------------------------------------------------


def wiki_link(op_name: str) -> str:
    return f"[[{op_name}]]"


def write_service_page(service: str, methods: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    lines.append(f"# Service: `{service}`")
    lines.append("")
    lines.append(f"**{len(methods)} methods** in this service.")
    lines.append("")
    for m in sorted(methods, key=lambda x: (x["method"], x["operation"])):
        verb = m["method"]
        op = m["operation"] or "(root)"
        lines.append(f"## `{verb} /{m['path'].strip('/')}`")
        lines.append(f"**Operation:** `{op}`")
        lines.append("")
        if m["summary"]:
            lines.append(f"**Summary:** {m['summary']}")
            lines.append("")
        if m["description"]:
            desc = m["description"]
            if len(desc) > 600:
                desc = desc[:600] + "…"
            lines.append(f"**Description:** {desc}")
            lines.append("")
        if m["parameters"]:
            lines.append("**Parameters:**")
            for p in m["parameters"]:
                req = "required" if p["required"] else "optional"
                lines.append(
                    f"- `{p['name']}` ({p['location']}, {req}) "
                    f"— {p['description'] or '_(no description)_'}"
                )
            lines.append("")
        rb = m.get("request_body")
        if rb and (rb["schema_refs"] or rb["required_fields"]):
            lines.append("**Request body:**")
            if rb["content_types"]:
                lines.append(f"- Content-Type: `{', '.join(rb['content_types'])}`")
            if rb["schema_refs"]:
                refs = ", ".join(f"`{r}`" for r in rb["schema_refs"])
                lines.append(f"- Schema: {refs}")
            if rb["required_fields"]:
                reqs = ", ".join(f"`{r}`" for r in rb["required_fields"])
                lines.append(f"- Required fields: {reqs}")
            lines.append("")
        if m["responses"]:
            lines.append("**Responses:**")
            for status, body in sorted(m["responses"].items()):
                schemas = ", ".join(f"`{s}`" for s in body["schema_refs"]) or "_(no schema)_"
                lines.append(f"- `{status}` — {body['description']} → {schemas}")
            lines.append("")
        # See-also: siblings in same service that might chain
        sibs = [o["operation"] for o in methods if o["operation"] != m["operation"]]
        if sibs:
            related = [
                s for s in sibs
                if any(token in s.lower() for token in m["operation"].lower().split("_"))
                and len(s) > 3
            ][:5]
            if related:
                lines.append("**Related:** " + " · ".join(wiki_link(s) for s in related))
                lines.append("")
        lines.append("---")
        lines.append("")
    (MAP_DIR / f"{service}.md").write_text("\n".join(lines), encoding="utf-8")


def write_master_index(records: list[dict[str, Any]]) -> None:
    """Top-level entry point for the map."""
    by_svc: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_svc[r["service"]].append(r)

    lines = ["# PrismHR API — Navigation Map", ""]
    lines.append(f"Total methods: **{len(records)}** · Services: **{len(by_svc)}**")
    lines.append("")
    lines.append("Drop this `.planning/map/` folder into an Obsidian vault for full cross-linking.")
    lines.append("")
    lines.append("## Services by size")
    lines.append("")
    lines.append("| Service | Methods | GET | POST | Link |")
    lines.append("|---|---:|---:|---:|---|")
    for svc, methods in sorted(by_svc.items(), key=lambda kv: -len(kv[1])):
        g = sum(1 for m in methods if m["method"] == "GET")
        p = sum(1 for m in methods if m["method"] == "POST")
        lines.append(f"| `{svc}` | {len(methods)} | {g} | {p} | [[{svc}]] |")
    lines.append("")
    (MAP_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    doc = pymupdf.open(PDF_PATH)
    full = "\n".join(doc[p].get_text() for p in range(doc.page_count))

    blocks = split_endpoint_blocks(full)
    records: list[dict[str, Any]] = []
    seen = set()
    for b in blocks:
        rec = parse_endpoint_block(b)
        if not rec:
            continue
        key = (rec["path"], rec["method"])
        if key in seen:
            continue
        seen.add(key)
        records.append(rec)

    print(f"parsed {len(records)} unique endpoints")

    (OUT_DIR / "prismhr-methods-full.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )

    schemas = extract_schemas(full)
    (OUT_DIR / "prismhr-schemas.json").write_text(
        json.dumps(schemas, indent=2), encoding="utf-8"
    )
    print(f"captured {len(schemas)} schema references")

    by_svc: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_svc[r["service"]].append(r)
    for svc, methods in by_svc.items():
        write_service_page(svc, methods)
    write_master_index(records)
    print(f"wrote {len(by_svc)} service pages to {MAP_DIR}")


if __name__ == "__main__":
    main()
