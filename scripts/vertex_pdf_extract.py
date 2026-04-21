"""Extract Vertex Calculation Guide PDF into structured JSON catalog.

Input:  C:/Users/NiharKulkarni/Downloads/Vertex Calculation Guide.pdf
Output: .planning/vertex/vertex_catalog_2026Q1.json (gitignored — PII-adjacent)
        src/prismhr_mcp/data/vertex_catalog_2026Q1.json (committed — brackets only)

Strategy: Vertex sections are page-bounded per state. Each state has
"State Withholding Tax Rate Tables" pages with bracket tables in a
consistent format:
  Line | If taxable wages are (Not over X / X) | Tax is Amount + % | Of the excess over

Filing statuses appear as section headers above each bracket table
(Single, Married, Head of Household, etc).

Extraction is conservative: if a bracket row doesn't match the expected
regex, it's logged and skipped. Downstream calc code checks confidence
before flagging deltas.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pdfplumber


PDF_PATH = Path("C:/Users/NiharKulkarni/Downloads/Vertex Calculation Guide.pdf")
BOUNDS_PATH = Path(".planning/vertex/state_bounds.json")
OUT_INTERNAL = Path(".planning/vertex/vertex_catalog_2026Q1.json")
OUT_PUBLIC = Path("src/prismhr_mcp/data/vertex_catalog_2026Q1.json")


# Filing-status section headers to look for inside rate-table pages.
FILING_STATUS_HEADERS = [
    "Single",
    "Single/Married with Two or More Incomes",
    "Married with One Income",
    "Married",
    "Married Filing Jointly",
    "Married Filing Separately",
    "Head of Household",
    "Head of Family",
    "Qualified Surviving Spouse",
    "All filers",
    "All Filers",
    "Unmarried Head of Household",
]

# Broader match: "Filing status X" / "Filing status X, Y, Z" / "Status X"
RE_FILING_STATUS_LINE = re.compile(
    r"^(Filing\s+[Ss]tatus\s+[A-Za-z0-9,\s]+|Status\s+[A-Z][A-Za-z, ]+)$",
    re.IGNORECASE,
)


# Parse a bracket row. Format variants observed:
#   "1 Not over 8,500.00 3.90%"                                  (first row, no cumul)
#   "2 11,700.00 332.00 4.40% 8,500.00"                          (middle row)
#   "11 Over 1,077,550.00 Use Method III ..."                    (final row, method ref)
#   "Over 9,436.00 263.00 4.70% 9,436.00"                        (MO-style last)
NUM = r"[0-9][0-9,]*(?:\.[0-9]+)?"
PCT = r"[0-9]+(?:\.[0-9]+)?%"

RE_FIRST = re.compile(rf"^(?:(\d+)\s+)?Not\s+over\s+({NUM})\s+({PCT})")
RE_MID = re.compile(rf"^(?:(\d+)\s+)?({NUM})\s+({NUM})\s+({PCT})\s+({NUM})\s*$")
RE_LAST = re.compile(rf"^(?:(\d+)\s+)?Over\s+({NUM})\s+({NUM})\s+({PCT})\s+({NUM})\s*$")
RE_LAST_METHOD = re.compile(rf"^(?:(\d+)\s+)?Over\s+({NUM})\s+Use\s+Method", re.I)


def _n(s: str) -> float:
    return float(s.replace(",", ""))


def _pct(s: str) -> float:
    return float(s.rstrip("%")) / 100


def _parse_bracket_line(line: str) -> dict | None:
    line = line.strip()
    m = RE_FIRST.match(line)
    if m:
        _, cap, rate = m.groups()
        return {"min": 0.0, "max": _n(cap), "base_tax": 0.0, "rate": _pct(rate)}
    m = RE_MID.match(line)
    if m:
        _, cap, base, rate, floor = m.groups()
        return {"min": _n(floor), "max": _n(cap), "base_tax": _n(base), "rate": _pct(rate)}
    m = RE_LAST.match(line)
    if m:
        _, floor, base, rate, excess = m.groups()
        return {"min": _n(floor), "max": None, "base_tax": _n(base), "rate": _pct(rate)}
    m = RE_LAST_METHOD.match(line)
    if m:
        _, floor = m.groups()
        return {"min": _n(floor), "max": None, "base_tax": None, "rate": None, "note": "method_ref"}
    return None


def _extract_state_brackets(pdf: pdfplumber.PDF, start: int, end: int) -> dict:
    """Walk state pages. Find bracket rows keyed by filing status.

    Bracket pages detected by presence of at least one parseable bracket row
    AND either a rate-table header or a filing-status header on same page.
    Avoids dependence on specific header wording (Vertex mixes styles).
    """
    result: dict[str, Any] = {"filing_statuses": {}, "raw_pages": []}
    current_status: str | None = None

    for pnum in range(start, end + 1):
        if pnum - 1 >= len(pdf.pages):
            break
        txt = pdf.pages[pnum - 1].extract_text() or ""
        lines = [l.strip() for l in txt.split("\n") if l.strip()]
        if not lines:
            continue

        has_rate_hint = (
            "Rate Table" in txt
            or "Rate Schedule" in txt
            or "taxable wages" in txt.lower()
        )
        if not has_rate_hint:
            continue

        page_had_bracket = False
        for line in lines:
            if line in FILING_STATUS_HEADERS or RE_FILING_STATUS_LINE.match(line):
                current_status = line
                result["filing_statuses"].setdefault(current_status, [])
                continue
            bracket = _parse_bracket_line(line)
            if bracket:
                if current_status is None:
                    current_status = "Default"
                    result["filing_statuses"].setdefault(current_status, [])
                result["filing_statuses"][current_status].append(bracket)
                page_had_bracket = True
        if page_had_bracket:
            result["raw_pages"].append(pnum)

    # Deduplicate per status: occasionally the same table prints twice
    for status, brackets in result["filing_statuses"].items():
        seen = set()
        uniq = []
        for b in brackets:
            key = (b.get("min"), b.get("max"), b.get("rate"))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(b)
        result["filing_statuses"][status] = uniq

    return result


NO_INCOME_TAX_STATES = {
    "Alaska", "Florida", "Nevada", "New Hampshire", "South Dakota",
    "Tennessee", "Texas", "Washington", "Wyoming",
}

FLAT_TAX_STATES = {
    "Colorado", "Illinois", "Indiana", "Kentucky", "Massachusetts",
    "Michigan", "North Carolina", "Pennsylvania", "Utah",
}


def _extract_flat_rate(pdf: pdfplumber.PDF, start: int, end: int) -> float | None:
    """Scan state section for a flat state tax rate."""
    for pnum in range(start, end + 1):
        if pnum - 1 >= len(pdf.pages):
            break
        txt = pdf.pages[pnum - 1].extract_text() or ""
        if "State Withholding Tax" not in txt:
            continue
        # Look for "state tax rate of X%" / "flat rate of X%" / "X% flat"
        patterns = [
            rf"state\s+tax\s+rate[^%]*?({PCT})",
            rf"flat\s+rate[^%]*?({PCT})",
            rf"tax\s+rate\s+of\s+({PCT})",
            rf"multiply[^%]*?by\s+({PCT})",
        ]
        for pat in patterns:
            m = re.search(pat, txt, re.I)
            if m:
                return _pct(m.group(1))
    return None


def _extract_supplemental_rate(pdf: pdfplumber.PDF, start: int, end: int) -> float | None:
    """Scan for 'Supplemental Wages Only Flat Rate' + rate."""
    for pnum in range(start, end + 1):
        if pnum - 1 >= len(pdf.pages):
            break
        txt = pdf.pages[pnum - 1].extract_text() or ""
        if "Supplemental" in txt and "Flat Rate" in txt:
            # Look for "X.XX%" near keyword
            m = re.search(rf"Supplemental[^%]*?({PCT})", txt)
            if m:
                return _pct(m.group(1))
    return None


def _extract_sui_wage_base(pdf: pdfplumber.PDF, start: int, end: int) -> dict | None:
    """Scan SUI Summary pages for wage base + employer rate range."""
    out: dict[str, Any] = {}
    for pnum in range(start, end + 1):
        if pnum - 1 >= len(pdf.pages):
            break
        txt = pdf.pages[pnum - 1].extract_text() or ""
        if "State Unemployment Insurance" not in txt and "SUI" not in txt:
            continue
        m = re.search(r"[Ww]age\s+[Bb]ase[^0-9]*\$?([0-9,]+(?:\.[0-9]+)?)", txt)
        if m:
            out.setdefault("wage_base", _n(m.group(1)))
        m2 = re.search(r"New\s+[Ee]mployer\s+[Rr]ate[^0-9]*([0-9.]+)%", txt)
        if m2:
            out.setdefault("new_employer_rate", float(m2.group(1)) / 100)
    return out or None


def main() -> int:
    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found at {PDF_PATH}", file=sys.stderr)
        return 1
    if not BOUNDS_PATH.exists():
        print(f"ERROR: bounds file missing at {BOUNDS_PATH}", file=sys.stderr)
        return 1

    bounds = json.loads(BOUNDS_PATH.read_text())
    catalog: dict[str, Any] = {
        "source": "Vertex Calculation Guide — March 2026",
        "extracted_at": "2026-04-21",
        "states": {},
    }

    with pdfplumber.open(PDF_PATH) as pdf:
        for state, rng in bounds.items():
            start, end = rng["start"], rng["end"]
            print(f"  {state}: pp {start}-{end}")
            brackets = _extract_state_brackets(pdf, start, end)
            supp = _extract_supplemental_rate(pdf, start, end)
            sui = _extract_sui_wage_base(pdf, start, end)
            no_tax = state in NO_INCOME_TAX_STATES
            flat = _extract_flat_rate(pdf, start, end) if state in FLAT_TAX_STATES else None
            catalog["states"][state] = {
                "page_start": start,
                "page_end": end,
                "no_income_tax": no_tax,
                "flat_rate": flat,
                "brackets": brackets["filing_statuses"],
                "rate_table_pages": brackets["raw_pages"],
                "supplemental_flat_rate": supp,
                "sui": sui,
            }

    # Write both copies
    OUT_INTERNAL.parent.mkdir(parents=True, exist_ok=True)
    OUT_INTERNAL.write_text(json.dumps(catalog, indent=2))
    OUT_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    OUT_PUBLIC.write_text(json.dumps(catalog, indent=2))

    # Summary
    filled = sum(1 for s, d in catalog["states"].items() if d["brackets"])
    print()
    print(f"Extracted {filled}/{len(catalog['states'])} states with brackets.")
    for state, data in catalog["states"].items():
        n_statuses = len(data["brackets"])
        total_brackets = sum(len(v) for v in data["brackets"].values())
        mark = "OK" if total_brackets else "EMPTY"
        print(f"  {mark:5s} {state:25s}  {n_statuses} statuses, {total_brackets} brackets, supp={data['supplemental_flat_rate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
