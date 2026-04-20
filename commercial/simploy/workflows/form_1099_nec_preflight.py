"""1099-NEC End-to-End Pre-flight — workflow #60.

Year-end 1099-NEC pipeline. For every contractor the client paid in
the tax year, this workflow answers three questions:

  1. Do we have a valid W-9 on file (TIN + legal name + address)?
  2. Does the TIN pass the IRS TIN-Match service (or at least our
     local checksum heuristics when the live TIN-Match API isn't wired)?
  3. Is the YTD nonemployee compensation computed correctly and above
     the $600 threshold that triggers 1099-NEC issuance?

Output: per-contractor record with 1099-NEC box 1 amount, backup-
withholding status, and a list of blockers before IRS FIRE/IRIS filing.

Findings:
  NO_W9_ON_FILE              contractor paid but no W-9 record
  TIN_MISSING                W-9 exists but TIN is blank
  TIN_INVALID_FORMAT         EIN/SSN doesn't match the 9-digit pattern
  TIN_MATCH_FAILED           IRS TIN-Match API returned a mismatch
  NAME_TIN_MISMATCH          legal name on W-9 doesn't agree with
                             what we paid (entity-name vs DBA)
  ADDRESS_INCOMPLETE         can't print/mail without full address
  BELOW_600_THRESHOLD        YTD nonemp comp < $600; no 1099 issued
                             (INFO, not a blocker — just skip)
  BACKUP_WITHHOLDING_REQUIRED TIN mismatch or missing -> 24% BWH
                             should have been withheld; check.
  BOX1_MISMATCH              YTD total in voucher ledger != what
                             would land on 1099 Box 1 (nonemp comp).

Inputs: client_id, tax_year.
Scope: read-only. Does NOT transmit to IRS — pre-flight only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str

_NEC_THRESHOLD = Decimal("600.00")
_BACKUP_WITHHOLDING_RATE = Decimal("0.24")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class ContractorAudit:
    contractor_id: str
    legal_name: str
    ein_or_ssn_masked: str
    ytd_nonemp_comp: Decimal
    ytd_backup_withholding: Decimal
    expected_backup_withholding: Decimal
    findings: list[Finding] = field(default_factory=list)

    @property
    def above_threshold(self) -> bool:
        return self.ytd_nonemp_comp >= _NEC_THRESHOLD

    @property
    def ready_to_file(self) -> bool:
        return self.above_threshold and not any(
            f.severity == "critical" for f in self.findings
        )


@dataclass
class Form1099NECReport:
    client_id: str
    tax_year: int
    as_of: date
    contractors: list[ContractorAudit]

    @property
    def total_above_threshold(self) -> int:
        return sum(1 for c in self.contractors if c.above_threshold)

    @property
    def ready_to_file(self) -> int:
        return sum(1 for c in self.contractors if c.ready_to_file)

    @property
    def blocked(self) -> int:
        return self.total_above_threshold - self.ready_to_file


class PrismHRReader(Protocol):
    async def list_contractors_paid_in_year(
        self, client_id: str, tax_year: int
    ) -> list[dict]:
        """Rows: contractorId, legalName, ein, ssn, ytdNonempComp,
        ytdBackupWithholding, w9OnFile, address (line1, city, state, zip)."""
        ...


class TINMatcher(Protocol):
    async def match(self, *, tin: str, legal_name: str) -> dict:
        """Returns {'matched': bool, 'code': int, 'detail': str}.
        Live implementations hit the IRS TIN-Match API. For pre-flight
        without the live service, fall back to the LocalTINChecksum stub."""
        ...


@dataclass
class LocalTINChecksum:
    """Fallback TIN validator when IRS TIN-Match isn't wired. Checks
    format only; never certifies a real match. Use ONLY as a sanity net."""

    async def match(self, *, tin: str, legal_name: str) -> dict:
        raw = (tin or "").replace("-", "").strip()
        if len(raw) != 9 or not raw.isdigit():
            return {"matched": False, "code": 1, "detail": "bad format"}
        # Rudimentary: SSN can't start with 000, 666, or 9xx.
        if raw.startswith("000") or raw.startswith("666") or raw[0] == "9":
            return {"matched": False, "code": 2, "detail": "invalid SSN prefix"}
        # EIN can't have 00 in positions 3-4.
        if raw[2:4] == "00":
            return {"matched": False, "code": 2, "detail": "invalid EIN prefix"}
        return {"matched": True, "code": 0, "detail": "format ok"}


async def run_form_1099_nec_preflight(
    reader: PrismHRReader,
    *,
    client_id: str,
    tax_year: int,
    as_of: date | None = None,
    tin_matcher: TINMatcher | None = None,
    tolerance: Decimal | str = "0.01",
) -> Form1099NECReport:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))
    matcher = tin_matcher or LocalTINChecksum()

    rows = await reader.list_contractors_paid_in_year(client_id, tax_year)
    audits: list[ContractorAudit] = []

    for row in rows:
        cid = str(row.get("contractorId") or row.get("employeeId") or "")
        if not cid:
            continue
        legal_name = str(row.get("legalName") or "").strip()
        ein = (row.get("ein") or "").strip()
        ssn = (row.get("ssn") or "").strip()
        tin_raw = ein or ssn
        tin_masked = _mask(tin_raw)
        ytd = _dec(row.get("ytdNonempComp"))
        ytd_bwh = _dec(row.get("ytdBackupWithholding"))
        w9 = bool(row.get("w9OnFile"))
        addr = row.get("address") or {}

        expected_bwh = Decimal("0")

        audit = ContractorAudit(
            contractor_id=cid,
            legal_name=legal_name,
            ein_or_ssn_masked=tin_masked,
            ytd_nonemp_comp=ytd,
            ytd_backup_withholding=ytd_bwh,
            expected_backup_withholding=expected_bwh,
        )

        below_threshold = ytd < _NEC_THRESHOLD

        if below_threshold:
            audit.findings.append(
                Finding(
                    "BELOW_600_THRESHOLD",
                    "info",
                    f"YTD nonemployee comp ${ytd} under ${_NEC_THRESHOLD}; "
                    f"no 1099-NEC required.",
                )
            )
            audits.append(audit)
            continue

        # ---- W-9 + TIN checks ----
        if not w9:
            audit.findings.append(
                Finding(
                    "NO_W9_ON_FILE",
                    "critical",
                    f"Paid contractor {cid} ${ytd} but no W-9 on file.",
                )
            )

        if not tin_raw:
            audit.findings.append(
                Finding("TIN_MISSING", "critical", "W-9 missing TIN.")
            )
        else:
            normalized = tin_raw.replace("-", "")
            if len(normalized) != 9 or not normalized.isdigit():
                audit.findings.append(
                    Finding(
                        "TIN_INVALID_FORMAT",
                        "critical",
                        f"TIN '{tin_masked}' must be 9 digits.",
                    )
                )
            else:
                m = await matcher.match(tin=normalized, legal_name=legal_name)
                if not m.get("matched"):
                    audit.findings.append(
                        Finding(
                            "TIN_MATCH_FAILED",
                            "critical",
                            f"TIN match failed ({m.get('detail') or 'unknown'}). "
                            "Backup withholding should apply.",
                        )
                    )
                    # Expected BWH = 24% of nonemp comp paid after mismatch date.
                    # We use the full YTD as a worst case for ops to review.
                    expected_bwh = (ytd * _BACKUP_WITHHOLDING_RATE).quantize(
                        Decimal("0.01")
                    )
                    audit.expected_backup_withholding = expected_bwh
                    if ytd_bwh + tol < expected_bwh:
                        audit.findings.append(
                            Finding(
                                "BACKUP_WITHHOLDING_REQUIRED",
                                "critical",
                                f"Expected BWH ${expected_bwh} (24% × ${ytd}); "
                                f"actually withheld ${ytd_bwh}.",
                            )
                        )

        # ---- Name/TIN sanity ----
        voucher_name = str(row.get("voucherPayeeName") or "").strip()
        if legal_name and voucher_name and legal_name.upper() != voucher_name.upper():
            audit.findings.append(
                Finding(
                    "NAME_TIN_MISMATCH",
                    "warning",
                    f"Vouchers paid '{voucher_name}' but W-9 legal name is "
                    f"'{legal_name}'. Entity-vs-DBA or data error?",
                )
            )

        # ---- Address ----
        if not (addr.get("line1") and addr.get("city") and addr.get("state") and addr.get("zip")):
            audit.findings.append(
                Finding(
                    "ADDRESS_INCOMPLETE",
                    "critical",
                    "W-9 address is incomplete; cannot print/mail 1099.",
                )
            )

        # ---- Box 1 tie-out ----
        box1 = _dec(row.get("box1Expected") or row.get("ytdNonempComp"))
        if box1 != ytd and (box1 - ytd).copy_abs() > tol:
            audit.findings.append(
                Finding(
                    "BOX1_MISMATCH",
                    "critical",
                    f"Ledger YTD ${ytd} differs from computed Box 1 ${box1}.",
                )
            )

        audits.append(audit)

    return Form1099NECReport(
        client_id=client_id,
        tax_year=tax_year,
        as_of=today,
        contractors=audits,
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")


def _mask(tin: str) -> str:
    if not tin:
        return ""
    normalized = tin.replace("-", "")
    if len(normalized) >= 4:
        return "***-**-" + normalized[-4:]
    return "***"
