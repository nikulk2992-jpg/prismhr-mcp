"""Refresh OH municipal tax seed from Ohio DoT Finder CSV.

Overnight run tried:
  https://thefinder.tax.ohio.gov/
  https://tax.ohio.gov/researcher/municipalities/municipal-income-tax
  https://www.ritaohio.com/TaxRatesTable
  https://ccatax.ci.cleveland.oh.us/?p=taxrates

Corporate network blocks these. Run this from a non-blocked network
to pull the full ~600 Ohio taxing municipalities into
`.planning/locals-data/oh_muni_full.json`.

Expected input: Ohio DoT Finder "Municipal Income Tax Rate Database"
CSV, columns: Municipality, Tax Rate, Credit Rate, Credit Factor/Limit,
Effective Date, Collector.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

OUT = Path(".planning/locals-data/oh_muni_full.json")


def _parse_csv(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample) if sample else csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        out: dict = {}
        for row in reader:
            # Normalize keys
            k = {str(x or "").strip().lower(): row[x] for x in row}
            muni = (k.get("municipality") or k.get("muni")
                    or k.get("name") or "").strip().upper()
            if not muni:
                continue
            try:
                rate = float((k.get("tax rate") or k.get("rate") or "0").replace("%", "")) / 100
                credit_rate = float((k.get("credit rate") or "100").replace("%", "")) / 100
                credit_limit_raw = k.get("credit factor") or k.get("credit limit") or "0"
                credit_limit = float(str(credit_limit_raw).replace("%", "")) / 100
                collector = (k.get("collector") or "SELF").strip().upper()
            except Exception:  # noqa: BLE001
                continue
            out[muni] = {
                "work_rate": rate,
                "resident_rate": rate,
                "credit_rate": credit_rate,
                "credit_limit": credit_limit,
                "collector": collector,
            }
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: refresh_oh_muni.py <finder_rates.csv>")
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Not found: {path}")
        return 2

    muni_rates = _parse_csv(path)
    print(f"Loaded {len(muni_rates)} municipalities")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"muni_rates": muni_rates}, indent=2))
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
