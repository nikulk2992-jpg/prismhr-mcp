"""I-9 / Document Expiration Sweep — workflow #2.

Scans for employee-facing documents nearing expiration. I-9 reverify
deadlines, driver license expirations, visa/EAD expirations, and
professional licenses. Missing a reverify deadline = ICE audit risk
($2,700 paperwork fines up to $27,000 per violation).

Findings per employee-document pair:
  - EXPIRED: document expired as of today.
  - EXPIRING_URGENT: expires within 30 days.
  - EXPIRING_SOON: expires within 60 days.
  - EXPIRING_PLANNED: expires within 90 days.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class DocAudit:
    employee_id: str
    doc_type: str
    expiration_date: date | None
    findings: list[Finding] = field(default_factory=list)


@dataclass
class DocExpirationReport:
    client_id: str
    as_of: date
    audits: list[DocAudit]

    @property
    def total(self) -> int:
        return len(self.audits)

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def get_doc_expirations(
        self, client_id: str, doc_types: list[str], days_out: int
    ) -> list[dict]: ...


async def run_doc_expiration_sweep(
    reader: PrismHRReader,
    *,
    client_id: str,
    doc_types: list[str] | None = None,
    as_of: date | None = None,
    days_out: int = 90,
) -> DocExpirationReport:
    today = as_of or date.today()
    types = doc_types or ["I9"]

    rows = await reader.get_doc_expirations(client_id, types, days_out)
    audits: list[DocAudit] = []
    for r in rows:
        eid = str(r.get("employeeId") or "")
        doc_type = str(r.get("docType") or r.get("documentType") or "")
        exp = _parse(r.get("expirationDate") or r.get("expireDate"))
        audit = DocAudit(
            employee_id=eid, doc_type=doc_type, expiration_date=exp
        )
        if exp:
            days = (exp - today).days
            if days < 0:
                audit.findings.append(
                    Finding(
                        "EXPIRED",
                        "critical",
                        f"{doc_type} expired {-days} days ago ({exp.isoformat()}).",
                    )
                )
            elif days <= 30:
                audit.findings.append(
                    Finding(
                        "EXPIRING_URGENT",
                        "critical",
                        f"{doc_type} expires in {days} days ({exp.isoformat()}).",
                    )
                )
            elif days <= 60:
                audit.findings.append(
                    Finding(
                        "EXPIRING_SOON",
                        "warning",
                        f"{doc_type} expires in {days} days ({exp.isoformat()}).",
                    )
                )
            elif days <= 90:
                audit.findings.append(
                    Finding(
                        "EXPIRING_PLANNED",
                        "info",
                        f"{doc_type} expires in {days} days ({exp.isoformat()}).",
                    )
                )
        audits.append(audit)

    return DocExpirationReport(client_id=client_id, as_of=today, audits=audits)


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
