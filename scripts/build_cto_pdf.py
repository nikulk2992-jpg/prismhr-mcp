"""Render the tax-filing-automation CTO scope to a Simploy-branded PDF."""

from __future__ import annotations

import os
import sys
from pathlib import Path


SKILL_DIR = Path(
    r"C:\Users\NiharKulkarni\AppData\Roaming\Claude\local-agent-mode-sessions"
    r"\skills-plugin\5974022d-9fb5-4866-958e-a28d9981f468"
    r"\860bc17f-2c4e-4730-8764-9af9309712bb\skills\simploy-branded-pdf"
)
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from simploy_pdf import SimployPDF  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
OUT = REPO / ".planning" / "Simploy-Tax-Filing-Automation-Scope.pdf"
LOGO = SKILL_DIR / "assets" / "simploy_logo.png"


def build() -> None:
    pdf = SimployPDF(
        title="TAX FILING AUTOMATION",
        subtitle="Scope & Data Insights — Prepared for Accounting Leadership",
        output_path=str(OUT),
        logo_path=str(LOGO),
    )

    # ---- 1. The problem today ----
    pdf.add_section("1. THE PROBLEM TODAY", [
        "Simploy remits payroll taxes to roughly 20-40 separate taxing authorities every quarter: "
        "the IRS, state revenue departments, state unemployment agencies, state disability / "
        "paid-family-leave funds, plus city tax offices and school districts in the states that "
        "levy them. Every authority has its own portal, its own form number and due date, its "
        "own file format, and its own cadence.",
        "Today Ops runs this manually: open PrismHR, pull the report, log in to each portal, "
        "type numbers in or upload a file, download the confirmation, save the PDF to "
        "SharePoint, email the rep. Repeat across every client × every quarter × every "
        "jurisdiction.",
        "At 245 clients and a long tail of jurisdictions, a typical quarter is several "
        "hundred individual filings — roughly 15 hours per client per quarter of Ops time.",
    ])

    # ---- 2. What we actually file ----
    pdf.add_section("2. WHAT WE ACTUALLY FILE", [
        "I scanned the last 12 months of voucher data across all 245 UAT clients (same data as "
        "prod) and pulled every unique tax code Simploy has ever remitted on. This is the "
        "ground truth of where Simploy owes returns.",
    ])

    # Federal
    pdf.add_subsection("FEDERAL (APPLIES TO EVERY CLIENT)", [])
    pdf.add_table(
        headers=["Return", "What it covers", "Cadence"],
        rows=[
            ["Form 941", "Federal income tax, FICA (SS + Medicare)", "Quarterly"],
            ["Form 940", "FUTA (federal unemployment)", "Annual"],
            ["W-2 / W-3", "Year-end wage statements", "Annual"],
            ["1099-NEC / 1099-MISC", "Contractor payments", "Annual"],
            ["EFT deposits", "Continuous tax deposits", "Monthly or semi-weekly"],
        ],
    )
    pdf.add_paragraph(
        "Federal is the easiest to automate — the IRS has stable APIs (MeF, FIRE, IRIS) "
        "that accept machine-submitted returns."
    )

    # State withholding
    pdf.add_subsection("STATE INCOME TAX WITHHOLDING (ACTUAL 12-MONTH DATA)", [])
    pdf.add_table(
        title="20 STATES WITH ACTIVE WITHHOLDING",
        headers=["State", "YTD withheld", "Clients", "Portal / Form"],
        rows=[
            ["MO (dominant)", "$204,352", "203", "MyTax MO / MO-941"],
            ["IL", "$12,813", "21", "MyTax Illinois / IL-941 (API)"],
            ["OH", "$9,566", "13", "OH Business Gateway / IT-501"],
            ["CA", "$4,659", "6", "EDD e-Services / DE 9 + DE 9C (API)"],
            ["IA", "$3,168", "2", "GovConnect Iowa / IA 44-095"],
            ["NJ", "$3,140", "2", "NJ Online Svc / NJ-927 (API)"],
            ["VA", "$3,125", "2", "VATAX / VA-5, VA-6"],
            ["KS", "$3,099", "5", "KDOR / KW-3, KW-5"],
            ["AZ", "$3,045", "6", "AZTaxes / A1-QRT"],
            ["GA", "$2,847", "4", "GTC / G-7"],
            ["CO", "$2,195", "5", "MyBizColorado / DR 1094"],
            ["IN", "$1,213", "3", "INTIME / WH-1"],
            ["NY", "$1,055", "2", "NYS OSC / NYS-45 (API)"],
            ["WI", "$981", "1", "MyTax WI / WT-6"],
            ["AR", "$797", "3", "ATAP / AR941PT"],
            ["HI", "$759", "1", "HI Tax Online / HW-14"],
            ["OK", "$591", "3", "OkTAP / WTH 10001"],
            ["MA", "$558", "1", "MassTaxConnect / M-941 (API)"],
            ["MI", "$543", "1", "MI Treasury / SUW 5080"],
            ["NC", "$226", "4", "NCDOR / NC-5Q"],
        ],
    )
    pdf.add_callout(
        "MO is 80% of state withholding volume because most clients are Missouri-based. "
        "States with bulk APIs available (CA, IL, NY, NJ, MA, MD, OR) are candidates for "
        "full automation."
    )

    # Locals
    pdf.add_subsection("LOCAL CITY, COUNTY, AND SCHOOL-DISTRICT TAXES", [])
    pdf.add_paragraph(
        "78 unique local jurisdictions appeared in Simploy voucher data. The heaviest "
        "footprint is Missouri (Saint Louis earnings tax) and Ohio (dozens of cities + "
        "school districts)."
    )
    pdf.add_table(
        title="MISSOURI LOCALS",
        headers=["Jurisdiction", "YTD withheld", "Clients"],
        rows=[
            ["Saint Louis, MO earnings tax (1%)", "$16,854", "73"],
            ["Saint Louis Soulard CID overlay", "$77", "1"],
            ["Kansas City, MO earnings tax (1%)", "$74", "1"],
        ],
    )
    pdf.add_paragraph(
        "Saint Louis earnings tax is by far the biggest local by volume — 73 of 245 clients "
        "remit to it. Filed through the St. Louis Collector of Revenue."
    )
    pdf.add_table(
        title="OHIO MUNICIPAL TAXES (30+ jurisdictions; top 10 shown)",
        headers=["City", "Type", "YTD", "Clients"],
        rows=[
            ["Mason, OH", "City (CIWT)", "$1,354", "3"],
            ["Fairlawn, Summit County", "City", "$1,047", "1"],
            ["Dayton, OH", "City", "$944", "1"],
            ["Portsmouth, Scioto County", "Resident CIWT", "$459", "1"],
            ["New Franklin, OH", "City", "$328", "1"],
            ["Amberley, Hamilton County", "City", "$294", "1"],
            ["Dayton (residents)", "RES CIWT", "$282", "2"],
            ["Cincinnati (residents)", "RES CIWT", "$138", "2"],
            ["Sharonville, Hamilton County", "City", "$137", "1"],
            ["Columbus, OH", "City", "$67", "1"],
        ],
    )
    pdf.add_callout(
        "Ohio has 600+ individual tax jurisdictions administered via RITA (Regional Income "
        "Tax Agency), CCA (Central Collection Agency), or direct-to-city portals. Ohio is "
        "the hardest automation target in the country."
    )
    pdf.add_table(
        title="OHIO SCHOOL DISTRICTS (5 so far)",
        headers=["District", "YTD", "Clients"],
        rows=[
            ["Harrison Township SD", "$134", "1"],
            ["Nelson Township SD", "$87", "1"],
            ["Freedom Township SD", "$81", "1"],
            ["Eaton SD", "$67", "1"],
            ["Van Buren Township SD", "$53", "1"],
        ],
    )

    # State programs
    pdf.add_subsection("STATE PROGRAMS (SDI / PFML / ETT)", [])
    pdf.add_table(
        headers=["Program", "State", "YTD", "Clients"],
        rows=[
            ["State Disability Insurance", "CA", "$1,910", "6"],
            ["Employment Training Tax", "CA", "$290", "5"],
            ["State PFML", "NJ", "$479", "2"],
            ["State Disability", "NJ", "$286", "2"],
            ["Other (Workforce / SWF)", "NJ", "$410", "2"],
        ],
    )
    pdf.add_paragraph(
        "13 states now run paid-family-leave programs (CA, NY, NJ, MA, CT, CO, OR, WA, DC, "
        "DE, MD, ME, MN), each with its own portal and cadence. As Simploy expands, these "
        "multiply."
    )

    # Summary
    pdf.add_subsection("FILING VOLUME SUMMARY", [])
    pdf.add_table(
        headers=["Category", "Distinct jurisdictions", "Biggest by volume"],
        rows=[
            ["Federal", "5-6 return types", "941, 940, W-2, 1099"],
            ["State income tax", "20 states active", "MO ($204K / 203 clients)"],
            ["State programs", "5 programs", "CA SDI, CA ETT, NJ PFML/SDI"],
            ["Local city income", "40+ jurisdictions", "St Louis MO ($17K / 73 clients)"],
            ["Ohio school districts", "5 (so far)", "Harrison / Nelson Townships"],
            ["Total unique tax codes", "128", "(in Simploy voucher history)"],
        ],
    )
    pdf.add_green_callout(
        "Median MO-only client: 3-4 returns per quarter. "
        "Multi-state or Ohio-employee client: 15-35 returns per quarter. "
        "The pain concentrates on multi-state + Ohio clients."
    )

    pdf.add_page_break()

    # ---- 3. Vision ----
    pdf.add_section("3. THE VISION", [
        "Instead of Ops filing by hand, the system does the following on a fixed schedule "
        "(end of each quarter):",
    ])
    pdf.add_bullet_list([
        "Reconciles first — runs 941 / state withholding / SUTA reconciliation workflows. "
        "If any flag a problem, filing stops until Ops fixes.",
        "Generates the file or submits the API call. For every jurisdiction, builds the "
        "correct filing in the correct format using PrismHR data.",
        "Submits automatically where possible. IRS + ~8 state APIs = fully automated. Tool "
        "POSTs the XML, receives the confirmation, stores in the filing tracker.",
        "Stages for one-click submit where it's not. Tool generates a pre-filled file, "
        "opens a deep link to the portal's upload page; Ops clicks \"submit\".",
        "Tracks everything — confirmation numbers, attempt dates, dollar amounts, supporting "
        "documents in an audit-ready ledger.",
    ])

    # ---- 4. Automation tiers ----
    pdf.add_section("4. THREE AUTOMATION TIERS", [
        "Not every authority will be fully automatic. The system grades each jurisdiction "
        "into one of three tiers.",
    ])
    pdf.add_table(
        headers=["Tier", "Mechanism", "Who qualifies", "Expected coverage"],
        rows=[
            ["A", "Real API submission", "IRS + CA EDD + NY OSC + IL + MA + OR + MD + NJ", "~40% of volume"],
            ["B", "Pre-built file + 1-click", "Most states via EFW2 / portal upload", "~50% of volume"],
            ["C", "Browser automation", "Ohio RITA/CCA, PA munis, small portals", "~8% of volume"],
            ["D", "Manual checklist", "MFA-only or ink-signature portals", "~2% of volume"],
        ],
    )

    # ---- 5. Phased build ----
    pdf.add_section("5. PHASED BUILD (11 WEEKS TOTAL)", [])
    pdf.add_table(
        headers=["Phase", "Elapsed", "Value delivered"],
        rows=[
            ["1 — File generation", "2 weeks", "File drafts ready; Ops still uploads manually"],
            ["2 — Federal + top APIs", "3 weeks", "~40% auto-submit (IRS, CA, IL, NY, etc.)"],
            ["3 — Portal staging", "2 weeks", "Remaining states = 1-click submit"],
            ["4 — Locals + PA + OH", "3 weeks", "Long tail (St Louis, OH munis) = 1-click"],
            ["5 — Tracker + audit log", "1 week", "Compliance-ready dashboard"],
        ],
    )
    pdf.add_callout(
        "Against ~14,700 hours/year of Ops filing work today, payback is measured in weeks "
        "even if only 20% of filings automate."
    )

    pdf.add_page_break()

    # ---- 6. CTO questions ----
    pdf.add_section("6. WHAT I NEED FROM THE CTO", [
        "To turn this scope into a real build plan, the following 11 answers would sharpen "
        "everything:",
    ])

    pdf.add_subsection("ABOUT THE CURRENT PROCESS", [])
    pdf.add_bullet_list([
        "1. Which tax filing service does Simploy use today? (MasterTax / Vertex / ADP "
        "SmartCompliance / direct-to-DOR?) This fundamentally changes the build.",
        "2. Who is Simploy's authorized signer for IRS MeF + state bulk filer programs?",
        "3. Where do filing confirmations land today — email, SharePoint, paper?",
        "4. Credential management — are state portal passwords in 1Password, in Ops heads, "
        "or in a spreadsheet?",
    ])

    pdf.add_subsection("ABOUT EDGE CASES", [])
    pdf.add_bullet_list([
        "5. Multi-state employees — how does Simploy split wages when an employee lives "
        "in one state and works in another?",
        "6. Corrections — what's the current process if a prior quarter needs amendment "
        "(941-X, state W-3 amendments)? How often does this happen?",
        "7. Deposits vs returns — does the same system handle tax money movement, or is "
        "there a separate deposit service (EFTPS, state EFTs)?",
    ])

    pdf.add_subsection("ABOUT DATA AND RISK", [])
    pdf.add_bullet_list([
        "8. Is there a master list of every client's active tax registrations (SUTA "
        "accounts, local registrations)?",
        "9. Are there custom forms that wouldn't show up in voucher tax data (workers comp "
        "audit returns, nonresident tax forms, state withholding reconciliation forms like "
        "MO-W-3 or CA DE 7)?",
        "10. Comfort level with browser automation for portals without APIs?",
        "11. Audit posture — if a DOR auditor asked for proof of Q3 2025 filing for client X, "
        "what evidence does Simploy currently produce? Sets the bar for the audit log.",
    ])

    # ---- 7. Risks ----
    pdf.add_section("7. RISKS AND OPEN QUESTIONS", [])
    pdf.add_bullet_list([
        "IRS MeF enrollment takes 4-6 weeks. Paperwork should start now regardless of when "
        "the code ships.",
        "Each state with a bulk API has its own transmitter enrollment (CA, IL, NY, MA, NJ, "
        "OR, MD all separate).",
        "Rate limits — most portals weren't designed for 200+ submissions per week from a "
        "single filer. Need backoff and filing spread.",
        "CAPTCHAs on some portals may force certain filings to stay Tier D manual.",
        "Retention — filed XML + confirmations need 7-10 year storage (IRS = 7, CA = 10).",
    ])

    # ---- Closing summary ----
    pdf.add_section("8. BOTTOM LINE", [])
    pdf.add_green_callout(
        "Simploy runs ~14,700 hours/year of Ops time on manual state + local + federal "
        "tax filing. The automation tool reconciles first, generates the correct file per "
        "jurisdiction, submits via API where possible (~40% of volume), and stages for "
        "one-click upload where not (~50%). Phased over 11 weeks, delivered in five "
        "tranches of value. First tranche (file generation) lands in 2 weeks."
    )

    pdf.build()


if __name__ == "__main__":
    build()
