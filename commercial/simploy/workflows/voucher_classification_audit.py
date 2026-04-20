"""Voucher Classification Audit — catches mis-classified payroll lines
BEFORE journal export to Intacct.

The recon workflows (941/940/state) answer "does the form tie to the
vouchers". This one answers a different question: "are the vouchers
themselves classified correctly". Symptoms that show up downstream:
  - contractor paid on a W-2 pay code    -> wrong W-2 + wrong 1099-NEC
  - FICA-exempt employee got FICA taxed  -> wrong 941 + wrong W-2 Box 3/5
  - union pay code taxed contrary to rule -> wrong union report + 941
  - non-union employee on union pay code  -> wrong dues + benefit line

Where possible, findings are derived from the voucher itself (probed
shape — earning[] + employeeTax[]). Classification metadata (emp type,
FICA-exempt flag, union roster, pay-code subject flags) is fetched via
the reader protocol so a mock can stand in.

Tax-deduction code map (from verified UAT voucher probe):
  00-10 = FIT
  00-11 = FICA Medicare
  00-12 = FICA OASDI / Social Security
  XX-20 = state income tax (XX = state 2-digit)
  XXXXXXXXX-31 = local (city) income tax

Finding codes:
  CONTRACTOR_W2_PAY_CODE       emp.type=1099, line uses W-2 pay code
  W2_CONTRACTOR_PAY_CODE       emp.type=W-2, line uses 1099 pay code
  FICA_EXEMPT_BUT_WITHHELD     emp.fica_exempt=true, SS or Medicare > 0
  FICA_EXEMPT_MISFLAG          active W-2 flagged FICA exempt, no allowlist
  FICA_NONEXEMPT_NOT_WITHHELD  emp earning wages, no SS/Medicare line
  MEDICARE_ADDL_MISSED         YTD > $200K, addl Medicare 0.9% not taken
  UNION_CODE_NON_UNION_EMP     pay_code.is_union=true, emp not in union
  UNION_DUES_MISSING           union employee + union pay code, no dues
  STATE_SUTA_MISMATCH          SUTA accrued to state != emp.work_state
  ZERO_TAX_TAXABLE_CODE        pay_code subject to tax X, tax X = 0
  NEGATIVE_TAX_POSITIVE_WAGES  wages > 0, tax < 0, not a correction

Input: client_id, period_start, period_end (or batch_ids list).
Output: per-voucher-line finding list with drill-through refs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterable, Protocol


Severity = str  # "critical" | "warning" | "info"


_FICA_MEDICARE_CODE_PREFIX = "00-11"
_FICA_OASDI_CODE_PREFIX = "00-12"
_ADDL_MEDICARE_THRESHOLD = Decimal("200000")
_ADDL_MEDICARE_RATE = Decimal("0.009")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class LineAudit:
    voucher_id: str
    employee_id: str
    pay_code: str
    amount: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class VoucherAudit:
    voucher_id: str
    employee_id: str
    pay_date: date | None
    total_earnings: Decimal
    lines: list[LineAudit] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        here = not any(f.severity == "critical" for f in self.findings)
        lines = all(
            not any(f.severity == "critical" for f in l.findings)
            for l in self.lines
        )
        return here and lines


@dataclass
class ClassificationReport:
    client_id: str
    period_start: date
    period_end: date
    as_of: date
    vouchers: list[VoucherAudit]

    @property
    def total(self) -> int:
        return len(self.vouchers)

    @property
    def clean(self) -> int:
        return sum(1 for v in self.vouchers if v.passed and not v.findings)

    @property
    def flagged(self) -> int:
        return sum(1 for v in self.vouchers if v.findings or any(l.findings for l in v.lines))


class PrismHRReader(Protocol):
    """Read surface. All methods are async so a live PrismHR adapter
    (see adapters.py) drops in beside an in-memory fake for tests."""

    async def list_vouchers_for_period(
        self, client_id: str, period_start: date, period_end: date
    ) -> list[dict]:
        """Voucher rows with earning[] + employeeTax[] as in the verified
        payroll.v1.getPayrollVoucherForBatch probe.  See
        .planning/verified-responses/payroll_getPayrollVoucherForBatch.json
        for the shape this workflow expects."""
        ...

    async def get_employee_tax_profile(
        self, client_id: str, employee_id: str
    ) -> dict:
        """{
          employeeType: "W2" | "1099" | "STATUTORY",
          ficaExempt: bool,
          medicareExempt: bool,
          futaExempt: bool,
          sutaExempt: bool,
          workState: str,          # e.g. "MO"
          unionId: str | None,     # None if not in a union
          ytdSocialSecurityWages: Decimal-ish,
          ytdMedicareWages: Decimal-ish,
          ytdAdditionalMedicareWithheld: Decimal-ish,
          # Additional fields used by FICA_EXEMPT_MISFLAG check. PrismHR
          # doesn't carry an exemption reason — the FICA Exempt control
          # is a plain checkbox under employee > tax tab. So we infer
          # legitimacy from (a) employee/position allowlist supplied by
          # the caller, (b) status + emp type + wages.
          status: "ACTIVE" | "TERMINATED" | "LEAVE" | ...,
          position: str,           # job title / position code
        }
        """
        ...

    async def get_pay_code_definition(
        self, client_id: str, pay_code: str
    ) -> dict:
        """{
          payCode: str,
          description: str,
          isContractor: bool,      # 1099-side pay code
          isUnion: bool,
          unionId: str | None,
          ficaSubject: bool,
          medicareSubject: bool,
          futaSubject: bool,
          sutaSubject: bool,
          stateSubject: bool,
        }
        """
        ...

    async def list_union_members(
        self, client_id: str, union_id: str
    ) -> list[str]:
        """Employee IDs currently on the union roster."""
        ...


async def run_voucher_classification_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    period_start: date,
    period_end: date,
    as_of: date | None = None,
    tolerance: Decimal | str = "0.01",
    fica_exempt_allowlist_ids: frozenset[str] = frozenset(),
    fica_exempt_allowlist_positions: frozenset[str] = frozenset(),
) -> ClassificationReport:
    """Allowlists let clients with legitimately FICA-exempt employees
    (churches with clergy, schools with student workers, organizations
    employing F-1/J-1 visa holders) suppress the FICA_EXEMPT_MISFLAG
    finding for those specific employees/positions.
    """
    today = as_of or date.today()
    tol = Decimal(str(tolerance))
    allow_ids = {s.upper() for s in fica_exempt_allowlist_ids}
    allow_positions = {s.upper() for s in fica_exempt_allowlist_positions}

    # ---- caches so we don't hammer the reader per line ----
    emp_cache: dict[str, dict] = {}
    paycode_cache: dict[str, dict] = {}
    union_cache: dict[str, set[str]] = {}

    async def emp(eid: str) -> dict:
        if eid not in emp_cache:
            emp_cache[eid] = await reader.get_employee_tax_profile(client_id, eid) or {}
        return emp_cache[eid]

    async def pcode(code: str) -> dict:
        if code not in paycode_cache:
            paycode_cache[code] = await reader.get_pay_code_definition(client_id, code) or {}
        return paycode_cache[code]

    async def union(uid: str) -> set[str]:
        if uid not in union_cache:
            roster = await reader.list_union_members(client_id, uid) or []
            union_cache[uid] = {str(x) for x in roster}
        return union_cache[uid]

    vouchers = await reader.list_vouchers_for_period(client_id, period_start, period_end)

    audits: list[VoucherAudit] = []
    for v in vouchers:
        vid = str(v.get("voucherId") or v.get("id") or "")
        eid = str(v.get("employeeId") or "")
        pay_date = _parse(v.get("payDate"))
        total_earn = _dec(v.get("totalEarnings"))

        audit = VoucherAudit(
            voucher_id=vid,
            employee_id=eid,
            pay_date=pay_date,
            total_earnings=total_earn,
        )

        if not vid or not eid:
            audits.append(audit)
            continue

        profile = await emp(eid)
        emp_type = str(profile.get("employeeType") or "W2").upper()
        fica_exempt = bool(profile.get("ficaExempt"))
        medicare_exempt = bool(profile.get("medicareExempt"))
        work_state = str(profile.get("workState") or "").upper()
        union_id = profile.get("unionId")
        emp_status = str(profile.get("status") or "ACTIVE").upper()
        position = str(profile.get("position") or "")

        tax_rows = _rows(v, "employeeTax")
        ss_tax = _sum_tax(tax_rows, _FICA_OASDI_CODE_PREFIX)
        medicare_tax = _sum_tax(tax_rows, _FICA_MEDICARE_CODE_PREFIX)
        # Row presence matters independently of amount. A high earner
        # over the SS wage base cap has a 00-12 row with $0 withheld and
        # `empOverLimitAmount` populated — that is NOT a misflag. Only
        # row-absence means FICA was skipped entirely.
        has_ss_row = _has_row(tax_rows, _FICA_OASDI_CODE_PREFIX)
        has_med_row = _has_row(tax_rows, _FICA_MEDICARE_CODE_PREFIX)

        # ---- voucher-level: FICA exempt but withheld ----
        if fica_exempt and (ss_tax > tol or medicare_tax > tol):
            audit.findings.append(
                Finding(
                    "FICA_EXEMPT_BUT_WITHHELD",
                    "critical",
                    f"Employee {eid} is FICA-exempt but voucher withheld "
                    f"SS ${ss_tax} / Medicare ${medicare_tax}.",
                )
            )

        # ---- voucher-level: FICA exempt misflag ----
        # Caught the real 941-balancing bug at Simploy client 001315 (EE
        # M12853 HARDIN BRYAN D, Laborer, Active, 1099=No, FICA Exempt=Yes).
        # PrismHR stores FICA Exempt as a plain checkbox on employee > tax
        # tab — no reason code, no justification field — so an operator
        # check-click has no audit trail. Any active W-2 with wages flagged
        # exempt is a critical review item unless pre-allowlisted. Legit
        # exemptions (clergy, students, F-1/J-1, railroad) are rare enough
        # to manage via explicit allowlist.
        allowlisted = (
            eid.upper() in allow_ids
            or (position and position.upper() in allow_positions)
        )
        if (
            fica_exempt
            and emp_type == "W2"
            and emp_status == "ACTIVE"
            and total_earn > tol
            and not allowlisted
        ):
            audit.findings.append(
                Finding(
                    "FICA_EXEMPT_MISFLAG",
                    "critical",
                    f"Employee {eid}"
                    f"{f' ({position})' if position else ''}"
                    f" is flagged FICA Exempt=Yes but is an active W-2 with "
                    f"${total_earn} in wages this period. PrismHR has no "
                    f"reason field for this flag, so verify in the employee "
                    f"tax tab that the checkbox is intentional. If legit "
                    f"(clergy/student/visa/railroad), add to "
                    f"fica_exempt_allowlist_ids. Otherwise the 941 will not "
                    f"balance.",
                )
            )

        # ---- voucher-level: FICA not withheld on taxable wages ----
        # Key: row-absence, not amount. A cap-hit voucher ($0 amount,
        # over-limit populated) still has the 00-11/00-12 rows present.
        # Only missing rows mean the system didn't evaluate FICA at all,
        # which points at a misflag or wrong pay-code config.
        has_w2_earnings = await _has_fica_subject_earnings(v, client_id, pcode)
        if (
            not fica_exempt
            and has_w2_earnings
            and not has_ss_row
            and not has_med_row
            and total_earn > tol
        ):
            audit.findings.append(
                Finding(
                    "FICA_NONEXEMPT_NOT_WITHHELD",
                    "critical",
                    f"Employee {eid} is not FICA-exempt and earned "
                    f"${total_earn} but SS + Medicare tax rows are absent "
                    f"from the voucher entirely (not a cap-hit case).",
                )
            )

        # ---- voucher-level: additional Medicare missed ----
        ytd_medicare_wages = _dec(profile.get("ytdMedicareWages"))
        ytd_addl_withheld = _dec(profile.get("ytdAdditionalMedicareWithheld"))
        if not medicare_exempt and ytd_medicare_wages > _ADDL_MEDICARE_THRESHOLD:
            expected_addl = (
                (ytd_medicare_wages - _ADDL_MEDICARE_THRESHOLD) * _ADDL_MEDICARE_RATE
            ).quantize(Decimal("0.01"))
            if ytd_addl_withheld + tol < expected_addl:
                audit.findings.append(
                    Finding(
                        "MEDICARE_ADDL_MISSED",
                        "critical",
                        f"Employee {eid} YTD Medicare wages ${ytd_medicare_wages}; "
                        f"expected addl Medicare ≥ ${expected_addl}, withheld "
                        f"${ytd_addl_withheld}.",
                    )
                )

        # ---- line-level checks ----
        for line in _rows(v, "earning"):
            code = str(line.get("payCode") or "").upper()
            if not code:
                continue
            amount = _dec(line.get("payAmount"))
            la = LineAudit(
                voucher_id=vid,
                employee_id=eid,
                pay_code=code,
                amount=amount,
            )

            pc = await pcode(code)
            is_contractor_code = bool(pc.get("isContractor"))
            is_union_code = bool(pc.get("isUnion"))
            code_union_id = pc.get("unionId")

            # worker classification
            if emp_type in {"1099", "CONTRACTOR"} and not is_contractor_code and amount > tol:
                la.findings.append(
                    Finding(
                        "CONTRACTOR_W2_PAY_CODE",
                        "critical",
                        f"{eid} is 1099 but pay code {code} is a W-2 code.",
                    )
                )
            if emp_type in {"W2", "STATUTORY"} and is_contractor_code and amount > tol:
                la.findings.append(
                    Finding(
                        "W2_CONTRACTOR_PAY_CODE",
                        "critical",
                        f"{eid} is {emp_type} but pay code {code} is a 1099 code.",
                    )
                )

            # union classification
            if is_union_code and code_union_id:
                roster = await union(str(code_union_id))
                if eid not in roster and amount > tol:
                    la.findings.append(
                        Finding(
                            "UNION_CODE_NON_UNION_EMP",
                            "critical",
                            f"{eid} not on union roster {code_union_id} but pay "
                            f"code {code} is union-flagged.",
                        )
                    )

            # Zero tax on a taxable code (sanity). Only flag lines with
            # amount > 0 on a FICA-subject code if the voucher-level FICA
            # finding didn't already cover it.
            if (
                pc.get("ficaSubject")
                and amount > tol
                and ss_tax <= tol
                and medicare_tax <= tol
                and not fica_exempt
                and "FICA_NONEXEMPT_NOT_WITHHELD" not in {f.code for f in audit.findings}
            ):
                la.findings.append(
                    Finding(
                        "ZERO_TAX_TAXABLE_CODE",
                        "warning",
                        f"Pay code {code} is FICA-subject; voucher has $0 FICA.",
                    )
                )

            # Negative tax, positive wage (data error unless 'C' correction)
            if amount > tol and _any_negative_tax(tax_rows) and str(v.get("type") or "").upper() != "C":
                la.findings.append(
                    Finding(
                        "NEGATIVE_TAX_POSITIVE_WAGES",
                        "critical",
                        f"Voucher has positive wages but a negative tax line (type={v.get('type')}).",
                    )
                )

            audit.lines.append(la)

        # ---- voucher-level: union dues missing ----
        if union_id:
            roster = await union(str(union_id))
            if eid in roster:
                has_union_line = False
                for l in _rows(v, "earning"):
                    lcode = str(l.get("payCode") or "").upper()
                    if lcode and (await pcode(lcode)).get("isUnion"):
                        has_union_line = True
                        break
                deductions = _rows(v, "deduction") or _rows(v, "employeeDeduction")
                has_dues = any(
                    "DUES" in str(d.get("deductionCode") or d.get("code") or "").upper()
                    for d in deductions
                )
                if has_union_line and not has_dues:
                    audit.findings.append(
                        Finding(
                            "UNION_DUES_MISSING",
                            "warning",
                            f"Union employee {eid} has union earnings but no dues deduction.",
                        )
                    )

        # ---- voucher-level: SUTA state mismatch ----
        v_suta_state = str(v.get("sutaState") or v.get("wcState") or "").upper()
        if work_state and v_suta_state and work_state != v_suta_state:
            audit.findings.append(
                Finding(
                    "STATE_SUTA_MISMATCH",
                    "warning",
                    f"Employee work state {work_state} but voucher SUTA/WC state {v_suta_state}.",
                )
            )

        audits.append(audit)

    return ClassificationReport(
        client_id=client_id,
        period_start=period_start,
        period_end=period_end,
        as_of=today,
        vouchers=audits,
    )


# ---------- helpers ----------


def _rows(body: dict, key: str) -> list[dict]:
    raw = body.get(key)
    if raw is None:
        return []
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    return []


def _sum_tax(rows: Iterable[dict], code_prefix: str) -> Decimal:
    total = Decimal("0")
    for r in rows:
        code = str(r.get("empTaxDeductCode") or "")
        if code.startswith(code_prefix):
            total += _dec(r.get("empTaxAmount"))
    return total


def _has_row(rows: Iterable[dict], code_prefix: str) -> bool:
    for r in rows:
        code = str(r.get("empTaxDeductCode") or "")
        if code.startswith(code_prefix):
            return True
    return False


def _any_negative_tax(rows: Iterable[dict]) -> bool:
    for r in rows:
        if _dec(r.get("empTaxAmount")) < 0:
            return True
    return False


async def _has_fica_subject_earnings(voucher: dict, client_id: str, pcode) -> bool:  # type: ignore[no-untyped-def]
    for line in _rows(voucher, "earning"):
        code = str(line.get("payCode") or "").upper()
        if not code:
            continue
        pc = await pcode(code)
        if pc.get("ficaSubject"):
            return True
    return False


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
