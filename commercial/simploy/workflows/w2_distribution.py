"""W-2 Distribution Assistant — workflow #54.

Given a client + tax year, pulls every employee's W-2 PDF from
PrismHR and routes it to the configured delivery channels (mail,
email, archive). The workflow layer is pure orchestration — actual
mail/email/archive sending lives behind pluggable adapter
protocols so operators can wire Lob, Graph, SharePoint (or test
fakes) without touching workflow code.

Findings per employee:
  - W2_UNAVAILABLE: no W-2 for the target year.
  - NO_MAILING_ADDRESS: cannot mail — physical address missing.
  - NO_ELECTRONIC_CONSENT: cannot email — electronic-consent flag
    not set on the employee record.
  - MAIL_FAILED / EMAIL_FAILED / ARCHIVE_FAILED: adapter raised.

Delivery modes (any combination):
  - "mail": print-and-mail via Lob-compatible adapter; certified
    mail is the recommended setting for IRS-required proof of delivery.
  - "email": Graph send with PDF attachment; only if employee opted
    into electronic receipt on file.
  - "archive": drop to a per-client SharePoint folder via Graph.

Local-test mode: if the mail/email adapters are given as LocalDryRun
stubs, the workflow writes PDFs to a local directory and emits a
structured "would have sent" manifest instead of hitting the wire.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Protocol


class DeliveryMode(str, Enum):
    MAIL = "mail"
    EMAIL = "email"
    ARCHIVE = "archive"


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class EmployeeW2Delivery:
    employee_id: str
    first_name: str
    last_name: str
    year: str
    pdf_size_bytes: int
    modes_attempted: list[DeliveryMode] = field(default_factory=list)
    mail_tracking_id: str | None = None
    mail_address_source: str | None = None  # "W2" or "PRIMARY"
    email_message_id: str | None = None
    archive_url: str | None = None
    findings: list[Finding] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return (
            any(self.modes_attempted)
            and not any(f.severity == "critical" for f in self.findings)
        )


@dataclass
class W2DistributionReport:
    client_id: str
    year: str
    as_of: date
    employees: list[EmployeeW2Delivery]

    @property
    def total(self) -> int:
        return len(self.employees)

    @property
    def delivered(self) -> int:
        return sum(1 for e in self.employees if e.succeeded)

    @property
    def failed(self) -> int:
        return self.total - self.delivered


# ---- Adapter protocols ----


class W2Source(Protocol):
    """Pulls the raw W-2 PDF + employee metadata from PrismHR."""

    async def list_employees_with_w2(
        self, client_id: str, year: str
    ) -> list[dict]: ...
    async def download_w2_pdf(
        self, client_id: str, employee_id: str, year: str
    ) -> bytes: ...
    async def get_employee_contact(
        self, client_id: str, employee_id: str
    ) -> dict: ...


class MailSender(Protocol):
    """Print-and-mail adapter. Lob-compatible contract."""

    async def send_letter(
        self,
        *,
        to_name: str,
        to_address: dict,
        pdf_bytes: bytes,
        certified: bool,
        metadata: dict,
    ) -> str: ...


class EmailSender(Protocol):
    """Email adapter. Graph-compatible contract."""

    async def send_email(
        self,
        *,
        to_address: str,
        subject: str,
        body: str,
        pdf_bytes: bytes,
        filename: str,
        metadata: dict,
    ) -> str: ...


class Archiver(Protocol):
    """File archive adapter. SharePoint-compatible contract."""

    async def upload(
        self, *, client_id: str, year: str, employee_id: str, pdf_bytes: bytes
    ) -> str: ...


# ---- Local-only dry-run stubs (used by dogfood / tests) ----


@dataclass
class LocalDryRunMailSender:
    """Writes PDFs to a local directory and returns a fake tracking id."""

    out_dir: Path
    counter: int = 0

    async def send_letter(
        self,
        *,
        to_name: str,
        to_address: dict,
        pdf_bytes: bytes,
        certified: bool,
        metadata: dict,
    ) -> str:
        self.counter += 1
        safe = to_name.replace(" ", "_").replace("/", "_") or "unknown"
        out = self.out_dir / "mail" / f"{safe}_{self.counter}.pdf"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pdf_bytes)
        manifest = self.out_dir / "mail_manifest.log"
        with manifest.open("a", encoding="utf-8") as f:
            cert = "certified" if certified else "first-class"
            f.write(f"{self.counter}\t{to_name}\t{to_address}\t{cert}\t{out}\n")
        return f"DRYRUN-MAIL-{self.counter:06d}"


@dataclass
class LocalDryRunEmailSender:
    out_dir: Path
    counter: int = 0

    async def send_email(
        self,
        *,
        to_address: str,
        subject: str,
        body: str,
        pdf_bytes: bytes,
        filename: str,
        metadata: dict,
    ) -> str:
        self.counter += 1
        safe = to_address.replace("@", "_at_").replace("/", "_")
        out = self.out_dir / "email" / f"{safe}_{self.counter}.pdf"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pdf_bytes)
        manifest = self.out_dir / "email_manifest.log"
        with manifest.open("a", encoding="utf-8") as f:
            f.write(f"{self.counter}\t{to_address}\t{subject}\t{out}\n")
        return f"DRYRUN-EMAIL-{self.counter:06d}"


@dataclass
class LocalDryRunArchiver:
    out_dir: Path

    async def upload(
        self, *, client_id: str, year: str, employee_id: str, pdf_bytes: bytes
    ) -> str:
        path = self.out_dir / "archive" / client_id / year / f"{employee_id}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pdf_bytes)
        return f"file://{path}"


# ---- Orchestration ----


async def run_w2_distribution(
    *,
    source: W2Source,
    mail_sender: MailSender | None,
    email_sender: EmailSender | None,
    archiver: Archiver | None,
    client_id: str,
    year: str,
    modes: list[DeliveryMode],
    as_of: date | None = None,
    max_employees: int = 1000,
    certified_mail: bool = True,
) -> W2DistributionReport:
    today = as_of or date.today()
    roster = await source.list_employees_with_w2(client_id, year)

    deliveries: list[EmployeeW2Delivery] = []
    for emp in roster[:max_employees]:
        eid = str(emp.get("employeeId") or "")
        if not eid:
            continue

        first = str(emp.get("firstName") or "")
        last = str(emp.get("lastName") or "")

        try:
            pdf = await source.download_w2_pdf(client_id, eid, year)
        except Exception as exc:  # noqa: BLE001
            rec = EmployeeW2Delivery(
                employee_id=eid,
                first_name=first,
                last_name=last,
                year=year,
                pdf_size_bytes=0,
            )
            rec.findings.append(
                Finding(
                    "W2_UNAVAILABLE",
                    "critical",
                    f"Could not pull W-2 PDF: {type(exc).__name__}: {str(exc)[:80]}",
                )
            )
            deliveries.append(rec)
            continue

        if not pdf or not pdf.startswith(b"%PDF"):
            rec = EmployeeW2Delivery(
                employee_id=eid,
                first_name=first,
                last_name=last,
                year=year,
                pdf_size_bytes=len(pdf),
            )
            rec.findings.append(
                Finding(
                    "W2_UNAVAILABLE",
                    "critical",
                    f"Response was not a PDF (len={len(pdf)}).",
                )
            )
            deliveries.append(rec)
            continue

        rec = EmployeeW2Delivery(
            employee_id=eid,
            first_name=first,
            last_name=last,
            year=year,
            pdf_size_bytes=len(pdf),
        )

        contact = await source.get_employee_contact(client_id, eid)

        if DeliveryMode.MAIL in modes and mail_sender is not None:
            addr = {
                "line1": contact.get("line1", ""),
                "line2": contact.get("line2", ""),
                "city": contact.get("city", ""),
                "state": contact.get("state", ""),
                "zip": contact.get("zip", ""),
            }
            if not addr["line1"] or not addr["city"] or not addr["state"]:
                rec.findings.append(
                    Finding("NO_MAILING_ADDRESS", "warning", "Cannot mail — address incomplete.")
                )
            else:
                rec.modes_attempted.append(DeliveryMode.MAIL)
                rec.mail_address_source = contact.get("address_source", "PRIMARY")
                try:
                    rec.mail_tracking_id = await mail_sender.send_letter(
                        to_name=f"{first} {last}".strip(),
                        to_address=addr,
                        pdf_bytes=pdf,
                        certified=certified_mail,
                        metadata={
                            "clientId": client_id,
                            "employeeId": eid,
                            "year": year,
                            "addressSource": rec.mail_address_source,
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    rec.findings.append(
                        Finding("MAIL_FAILED", "critical", f"{type(exc).__name__}: {str(exc)[:80]}")
                    )

        if DeliveryMode.EMAIL in modes and email_sender is not None:
            if not contact.get("consentsElectronic", False):
                rec.findings.append(
                    Finding(
                        "NO_ELECTRONIC_CONSENT",
                        "warning",
                        "Cannot email — employee has not opted into electronic W-2 delivery.",
                    )
                )
            elif not contact.get("email"):
                rec.findings.append(
                    Finding("NO_EMAIL_ON_FILE", "warning", "Cannot email — no email address.")
                )
            else:
                rec.modes_attempted.append(DeliveryMode.EMAIL)
                try:
                    rec.email_message_id = await email_sender.send_email(
                        to_address=contact["email"],
                        subject=f"Your {year} Form W-2",
                        body=(
                            f"Attached is your {year} Form W-2 from payroll.\n"
                            "Keep this document for your tax records."
                        ),
                        pdf_bytes=pdf,
                        filename=f"{eid}_W2_{year}.pdf",
                        metadata={"clientId": client_id, "employeeId": eid, "year": year},
                    )
                except Exception as exc:  # noqa: BLE001
                    rec.findings.append(
                        Finding("EMAIL_FAILED", "critical", f"{type(exc).__name__}: {str(exc)[:80]}")
                    )

        if DeliveryMode.ARCHIVE in modes and archiver is not None:
            rec.modes_attempted.append(DeliveryMode.ARCHIVE)
            try:
                rec.archive_url = await archiver.upload(
                    client_id=client_id, year=year, employee_id=eid, pdf_bytes=pdf
                )
            except Exception as exc:  # noqa: BLE001
                rec.findings.append(
                    Finding("ARCHIVE_FAILED", "warning", f"{type(exc).__name__}: {str(exc)[:80]}")
                )

        deliveries.append(rec)

    return W2DistributionReport(
        client_id=client_id, year=year, as_of=today, employees=deliveries
    )
