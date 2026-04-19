"""W-2 Distribution workflow — unit tests with in-memory fakes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.w2_distribution import (  # noqa: E402
    DeliveryMode,
    LocalDryRunArchiver,
    LocalDryRunEmailSender,
    LocalDryRunMailSender,
    run_w2_distribution,
)


class FakeSource:
    def __init__(self, roster, pdfs, contacts):
        self.roster = roster
        self.pdfs = pdfs
        self.contacts = contacts

    async def list_employees_with_w2(self, cid, year):
        return self.roster

    async def download_w2_pdf(self, cid, eid, year):
        return self.pdfs.get(eid, b"")

    async def get_employee_contact(self, cid, eid):
        return self.contacts.get(eid, {})


@pytest.mark.asyncio
async def test_mail_path_writes_local_pdf(tmp_path: Path) -> None:
    pdf_bytes = b"%PDF-1.4\n%fake w2 contents"
    src = FakeSource(
        roster=[{"employeeId": "E1", "firstName": "Ada", "lastName": "Lovelace"}],
        pdfs={"E1": pdf_bytes},
        contacts={"E1": {"line1": "1 Analytical Rd", "city": "London", "state": "NE", "zip": "68102"}},
    )
    mail = LocalDryRunMailSender(out_dir=tmp_path)
    report = await run_w2_distribution(
        source=src,
        mail_sender=mail,
        email_sender=None,
        archiver=None,
        client_id="T",
        year="2025",
        modes=[DeliveryMode.MAIL],
    )
    assert report.delivered == 1
    assert report.employees[0].mail_tracking_id is not None
    pdfs_written = list((tmp_path / "mail").iterdir())
    assert len(pdfs_written) == 1
    assert pdfs_written[0].read_bytes() == pdf_bytes


@pytest.mark.asyncio
async def test_missing_address_blocks_mail(tmp_path: Path) -> None:
    src = FakeSource(
        roster=[{"employeeId": "E2", "firstName": "A", "lastName": "B"}],
        pdfs={"E2": b"%PDF-1.4\nx"},
        contacts={"E2": {"line1": "", "city": "", "state": ""}},
    )
    mail = LocalDryRunMailSender(out_dir=tmp_path)
    report = await run_w2_distribution(
        source=src,
        mail_sender=mail,
        email_sender=None,
        archiver=None,
        client_id="T",
        year="2025",
        modes=[DeliveryMode.MAIL],
    )
    codes = {f.code for f in report.employees[0].findings}
    assert "NO_MAILING_ADDRESS" in codes


@pytest.mark.asyncio
async def test_email_requires_electronic_consent(tmp_path: Path) -> None:
    src = FakeSource(
        roster=[{"employeeId": "E3", "firstName": "A", "lastName": "B"}],
        pdfs={"E3": b"%PDF-1.4\nx"},
        contacts={"E3": {"email": "a@b.co", "consentsElectronic": False}},
    )
    email = LocalDryRunEmailSender(out_dir=tmp_path)
    report = await run_w2_distribution(
        source=src,
        mail_sender=None,
        email_sender=email,
        archiver=None,
        client_id="T",
        year="2025",
        modes=[DeliveryMode.EMAIL],
    )
    codes = {f.code for f in report.employees[0].findings}
    assert "NO_ELECTRONIC_CONSENT" in codes


@pytest.mark.asyncio
async def test_email_path_writes_local(tmp_path: Path) -> None:
    src = FakeSource(
        roster=[{"employeeId": "E4", "firstName": "Grace", "lastName": "Hopper"}],
        pdfs={"E4": b"%PDF-1.4\nhopper"},
        contacts={"E4": {"email": "grace@navy.mil", "consentsElectronic": True}},
    )
    email = LocalDryRunEmailSender(out_dir=tmp_path)
    report = await run_w2_distribution(
        source=src,
        mail_sender=None,
        email_sender=email,
        archiver=None,
        client_id="T",
        year="2025",
        modes=[DeliveryMode.EMAIL],
    )
    assert report.employees[0].email_message_id is not None


@pytest.mark.asyncio
async def test_archive_path_writes_local(tmp_path: Path) -> None:
    src = FakeSource(
        roster=[{"employeeId": "E5", "firstName": "A", "lastName": "B"}],
        pdfs={"E5": b"%PDF-1.4\narchive"},
        contacts={"E5": {}},
    )
    arch = LocalDryRunArchiver(out_dir=tmp_path)
    report = await run_w2_distribution(
        source=src,
        mail_sender=None,
        email_sender=None,
        archiver=arch,
        client_id="ACME",
        year="2025",
        modes=[DeliveryMode.ARCHIVE],
    )
    assert (tmp_path / "archive" / "ACME" / "2025" / "E5.pdf").exists()
    assert report.employees[0].archive_url.startswith("file://")


@pytest.mark.asyncio
async def test_non_pdf_response_flags_unavailable(tmp_path: Path) -> None:
    src = FakeSource(
        roster=[{"employeeId": "E6", "firstName": "A", "lastName": "B"}],
        pdfs={"E6": b"<html>error</html>"},
        contacts={"E6": {}},
    )
    report = await run_w2_distribution(
        source=src,
        mail_sender=LocalDryRunMailSender(out_dir=tmp_path),
        email_sender=None,
        archiver=None,
        client_id="T",
        year="2025",
        modes=[DeliveryMode.MAIL],
    )
    codes = {f.code for f in report.employees[0].findings}
    assert "W2_UNAVAILABLE" in codes


@pytest.mark.asyncio
async def test_all_three_modes_compose(tmp_path: Path) -> None:
    src = FakeSource(
        roster=[{"employeeId": "E7", "firstName": "A", "lastName": "B"}],
        pdfs={"E7": b"%PDF-1.4\nfull"},
        contacts={"E7": {
            "line1": "123 X St", "city": "Y", "state": "NE", "zip": "68102",
            "email": "a@b.co", "consentsElectronic": True,
        }},
    )
    report = await run_w2_distribution(
        source=src,
        mail_sender=LocalDryRunMailSender(out_dir=tmp_path),
        email_sender=LocalDryRunEmailSender(out_dir=tmp_path),
        archiver=LocalDryRunArchiver(out_dir=tmp_path),
        client_id="T",
        year="2025",
        modes=[DeliveryMode.MAIL, DeliveryMode.EMAIL, DeliveryMode.ARCHIVE],
    )
    emp = report.employees[0]
    assert emp.mail_tracking_id
    assert emp.email_message_id
    assert emp.archive_url
    assert set(emp.modes_attempted) == {DeliveryMode.MAIL, DeliveryMode.EMAIL, DeliveryMode.ARCHIVE}
