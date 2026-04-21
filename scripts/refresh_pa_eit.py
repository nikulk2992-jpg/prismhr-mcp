"""Refresh PA EIT seed table from DCED Tax Register.

Overnight run tried to auto-fetch from:
  https://munstats.pa.gov/Public/ReportInformation2.aspx?report=CLGSReportingSetup
  https://dced.pa.gov/download/psd-codes-xls/?wpdmdl=59377

Corporate network blocks both. This script lives as the refresh
pipeline: when you can reach DCED directly (e.g. from home network),
run this to pull the full 2,900+ PSD rate table into
`.planning/locals-data/pa_eit_full.json` where `pa_eit` will pick
it up as an override on top of the hardcoded seed.

Expected input formats:
  1. DCED Tax Register XLS (preferred) — 2900 rows, columns: PSD,
     County, Municipality, School District, Resident Rate,
     Nonresident Rate, LST.
  2. PA Dept of Revenue CSV (alt) — occasionally published as a
     snapshot for payroll vendors.

Usage:
  .venv/Scripts/python scripts/refresh_pa_eit.py path/to/tax_register.xls

If no arg supplied, tries the default download URLs (will fail
on blocked networks).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(".planning/locals-data/pa_eit_full.json")


def _parse_xls(path: Path) -> dict:
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise SystemExit(f"Empty workbook {path}")
    # Find header row
    hdr = None
    for i, row in enumerate(rows[:10]):
        cells = [str(c or "").strip().lower() for c in row]
        if any("psd" in c for c in cells):
            hdr = (i, cells)
            break
    if hdr is None:
        raise SystemExit("Could not find PSD header row")
    hi, hcells = hdr
    # Column index heuristics
    col = {
        "psd": next((i for i, c in enumerate(hcells) if "psd" in c), None),
        "muni": next((i for i, c in enumerate(hcells) if "muni" in c), None),
        "county": next((i for i, c in enumerate(hcells) if "county" in c), None),
        "res": next((i for i, c in enumerate(hcells) if "resident" in c), None),
        "nonres": next((i for i, c in enumerate(hcells) if "nonres" in c), None),
        "lst": next((i for i, c in enumerate(hcells) if "lst" in c or "local services" in c), None),
    }
    out: dict = {}
    for row in rows[hi + 1:]:
        try:
            psd = str(row[col["psd"]]).strip().replace("-", "").zfill(6) if col["psd"] is not None else None
            if not psd or not psd.isdigit():
                continue
            out[psd] = {
                "name": str(row[col["muni"]] or "").strip() if col["muni"] is not None else "",
                "county": str(row[col["county"]] or "").strip().upper() if col["county"] is not None else "",
                "resident": float(row[col["res"]] or 0) if col["res"] is not None else 0.0,
                "nonresident": float(row[col["nonres"]] or 0) if col["nonres"] is not None else 0.0,
                "lst_annual": int(row[col["lst"]] or 0) if col["lst"] is not None else 0,
                "outside_act_32": psd == "510101",
            }
        except Exception:  # noqa: BLE001
            continue
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: refresh_pa_eit.py <tax_register.xls>")
        print("No arg supplied; attempting direct download…")
        try:
            import httpx
            url = "https://dced.pa.gov/download/psd-codes-xls/?wpdmdl=59377"
            r = httpx.get(url, follow_redirects=True, timeout=60.0)
            if r.status_code != 200 or b"%PDF" in r.content[:10]:
                print(f"Download failed or returned PDF. Status={r.status_code}")
                return 2
            tmp = Path("/tmp/pa_register.xls")
            tmp.write_bytes(r.content)
            path = tmp
        except Exception as e:  # noqa: BLE001
            print(f"Fetch failed: {e}")
            return 2
    else:
        path = Path(sys.argv[1])
        if not path.exists():
            print(f"File not found: {path}")
            return 2

    print(f"Parsing {path}…")
    psd_rates = _parse_xls(path)
    print(f"Loaded {len(psd_rates)} PSD codes")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"psd_rates": psd_rates}, indent=2))
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
