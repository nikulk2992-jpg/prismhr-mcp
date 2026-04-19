"""Build .planning/prismhr-api-map.md from .planning/prismhr-methods.json.

Run after `scripts/extract_prismhr_methods.py` (or the inline extractor
already run) populates prismhr-methods.json. Produces a human-readable
catalog: service counts, MCP layout proposal, full per-service method
lists with GET/POST split.
"""

from __future__ import annotations

import json
import pathlib
from collections import defaultdict

SERVICE_MAPPING = {
    "clientMaster":    ("client",       "Clients & Worksites"),
    "employee":        ("employee",     "Employees & HR"),
    "payroll":         ("payroll",      "Payroll"),
    "benefits":        ("benefits",     "Benefits & PTO"),
    "deductions":      ("deductions",   "Deductions & Garnishments"),
    "codeFiles":       ("codes",        "Code Files (Reference Data)"),
    "humanResources":  ("hr",           "HR Operations"),
    "taxRate":         ("tax",          "Tax Setup & Rates"),
    "timesheet":       ("timesheet",    "Timesheet & Time Entry"),
    "newHire":         ("onboarding",   "New Hire / Onboarding"),
    "generalLedger":   ("gl",           "General Ledger & AR"),
    "documentService": ("documents",    "Document Management"),
    "applicant":       ("applicant",    "Applicant Tracking"),
    "prismSecurity":   ("security",     "Security & User Admin"),
    "system":          ("system",       "System"),
    "subscription":    ("subscription", "API Subscriptions"),
    "signOn":          ("signon",       "Sign-On (SSO)"),
    "login":           ("session",      "Session / Auth (internal)"),
}


def main() -> None:
    src = pathlib.Path(".planning/prismhr-methods.json")
    methods = json.loads(src.read_text(encoding="utf-8"))
    by_svc: dict[str, list[dict]] = defaultdict(list)
    for m in methods:
        by_svc[m["service"]].append(m)

    out: list[str] = []
    out.append("# PrismHR API Surface — Full Method Map")
    out.append("")
    out.append(
        "Source: `prismapi_full_bible_with_index.pdf` (extracted 2026-04-19). "
        "Raw JSON at `.planning/prismhr-methods.json`."
    )
    out.append("")
    out.append(f"**Total: {len(methods)} methods across {len(by_svc)} services.**")
    out.append("")

    # Summary table
    out.append("## Surface summary")
    out.append("")
    out.append("| Service | Methods | GET | POST | MCP group | Scopes | PEO domain |")
    out.append("|---|---:|---:|---:|---|---|---|")
    total_get = total_post = 0
    for svc, items in sorted(by_svc.items(), key=lambda kv: -len(kv[1])):
        g = sum(1 for i in items if i["method"] == "GET")
        p = sum(1 for i in items if i["method"] == "POST")
        total_get += g
        total_post += p
        scope_prefix, category = SERVICE_MAPPING.get(svc, ("unmapped", "?"))
        scopes = []
        if g:
            scopes.append(f"`{scope_prefix}:read`")
        if p:
            scopes.append(f"`{scope_prefix}:write`")
        out.append(
            f"| `{svc}` | {len(items)} | {g} | {p} | `{scope_prefix}` | "
            f"{', '.join(scopes)} | {category} |"
        )
    out.append(
        f"| **TOTAL** | **{len(methods)}** | **{total_get}** | **{total_post}** | — | — | — |"
    )
    out.append("")

    # Layout strategy
    out.append("## MCP layout strategy")
    out.append("")
    out.append(
        "Three tool tiers stack side by side. The goal: **a PEO ops user says "
        "'reconcile this batch' and Claude picks the right tool.** No one calls "
        "`payroll_register_reconcile(client_id=..., batch_id=..., threshold_pct=0.05)` "
        "directly."
    )
    out.append("")
    out.append("1. **Workflow tools (hand-written).** The headline moat. "
               "Composable PEO ops: `client_list`, `payroll_superbatch_status`, "
               "`payroll_register_reconcile`, `benefits_audit_discrepancies`. "
               "These combine several raw calls + domain logic.")
    out.append("")
    out.append("2. **Raw escape-hatch (single tool).** `prismhr_raw_request(service, "
               "operation, params)` — when the workflow tools don't cover a use "
               "case, Claude can still hit any PrismHR endpoint the account's "
               "upstream permissions allow. Scope-gated on a per-service basis.")
    out.append("")
    out.append("3. **Meta tools.** Session, permission, introspection.")
    out.append("")
    out.append(
        "Auto-registering all 447 methods as individual tools would flood "
        "Claude's tool-picker context. Keep the handful of curated workflow "
        "tools sharp; expose the long tail through one discoverable escape-hatch."
    )
    out.append("")

    # Per-service detail
    out.append("## Service catalog")
    out.append("")
    for svc, items in sorted(by_svc.items(), key=lambda kv: -len(kv[1])):
        scope_prefix, category = SERVICE_MAPPING.get(svc, ("unmapped", "?"))
        out.append(f"### `{svc}` — {category} ({len(items)} methods)")
        out.append("")
        out.append(f"**MCP group:** `{scope_prefix}` · **Scopes:** "
                   f"`{scope_prefix}:read`, `{scope_prefix}:write`")
        out.append("")
        gets = sorted([i for i in items if i["method"] == "GET"],
                      key=lambda r: r["operation"])
        posts = sorted([i for i in items if i["method"] == "POST"],
                       key=lambda r: r["operation"])
        if gets:
            out.append(f"<details><summary>Read methods (GET, {len(gets)})</summary>")
            out.append("")
            for r in gets:
                out.append(f"- `GET {r['path']}` — {r['summary']}")
            out.append("")
            out.append("</details>")
            out.append("")
        if posts:
            out.append(f"<details><summary>Write methods (POST, {len(posts)})</summary>")
            out.append("")
            for r in posts:
                out.append(f"- `POST {r['path']}` — {r['summary']}")
            out.append("")
            out.append("</details>")
            out.append("")

    # Workflow roadmap
    out.append("## Workflow tools — Phase 3+ roadmap")
    out.append("")
    out.append("Each workflow tool composes multiple raw methods with PEO semantics. "
               "Goal: one tool call = one natural-language ops request.")
    out.append("")
    out.append("### Group 3 — Benefits & Deductions")
    out.append("")
    out.append("- `benefits_elections(client_id, employee_id)` — active plans + enrollment status")
    out.append("- `benefits_deduction_schedule(client_id, employee_id)` — scheduled deductions + code metadata")
    out.append("- `benefits_audit_discrepancies(client_id, employee_id)` — diff active plans vs. scheduled deductions")
    out.append("- `benefits_aca_status(client_id, employee_id, year)` — monthly ACA + 1095-C history")
    out.append("- `benefits_cobra_eligibles(client_id)` — COBRA-eligible roster")
    out.append("- `benefits_carrier_sync(client_id)` — confirmation drift analysis")
    out.append("")
    out.append("### Group 4 — Compliance & Reporting")
    out.append("")
    out.append("- `compliance_w2_status(client_id, year)` — W2 + 1099 availability")
    out.append("- `compliance_garnishments(client_id, employee_id)` — garnishment orders + payment history")
    out.append("- `compliance_state_tax_setup(client_id)` — state tax rate audit")
    out.append("- `compliance_i9_audit(client_id)` — E-Verify status roster")
    out.append("- `compliance_workers_comp(client_id)` — WC codes + modifiers")
    out.append("- `compliance_941_reconcile(client_id, quarter)` — payroll register vs. tax deposits")
    out.append("")
    out.append("### Group 5 — Billing & Client Financials")
    out.append("")
    out.append("- `billing_client_rates(client_id)` — SUTA + billing codes + unbundled rules")
    out.append("- `billing_invoice_summary(client_id, date_range)` — outstanding invoices")
    out.append("- `billing_ar_status(client_id)` — aging + cash receipts")
    out.append("- `billing_audit_vs_payroll(client_id, batch_id)` — voucher vs. invoice reconciliation")
    out.append("- `billing_employer_tax_liability(client_id, date_range)` — employer-side tax owed")
    out.append("")
    out.append("### New groups beyond the original 48-tool plan")
    out.append("")
    out.append("- **`onboarding`** — 8 newHire methods unlock: `onboarding_start_ep_hire`, "
               "`onboarding_commit_batch`, `onboarding_status`, `onboarding_cancel_batch`")
    out.append("- **`applicant`** — 3 methods: `applicant_create`, `applicant_list`")
    out.append("- **`documents`** — 4 methods: `documents_upload`, `documents_types`, SSO-aware")
    out.append("- **`timesheet`** — 7 methods: `timesheet_add`, `timesheet_approve`, hook for external time systems")
    out.append("- **`signon`** — 11 methods: SSO token flow for Cowork / white-label portals")
    out.append("")
    out.append("### Decidedly out of scope (v1)")
    out.append("")
    out.append("- `prismSecurity` (17 methods) — user admin, admin-console-only")
    out.append("- `subscription` (7 methods) — API subscription mgmt, internal")
    out.append("")

    # ---- Tier-2 design (deferred; documented here so later sessions start aligned) ----
    out.append("## Tier-2 design — capability catalog (DEFERRED)")
    out.append("")
    out.append(
        "The first version of this map proposed a single `prismhr_raw_request` "
        "escape-hatch for the 447-method long tail. That throws away schema "
        "validation, argument hints, and response-shape expectations — Claude "
        "would confidently call wrong methods and misreport results."
    )
    out.append("")
    out.append("Replacement design, to build alongside Phase 3:")
    out.append("")
    out.append(
        "- **`capability_search(intent_phrase)`** — full-text search over the "
        "447-method catalog. Returns top-K matching methods with summary, "
        "service, and a stable `method_id` (e.g. `benefits.v1.getPaidTimeOff`)."
    )
    out.append(
        "- **`describe_operation(method_id)`** — returns the full per-method "
        "contract: parameters (query/header/body), required vs optional, shape "
        "of the response (from OpenAPI `#/components/schemas`), known empty "
        "conventions (list endpoint? 404→empty? 500→empty?), and the MCP "
        "scope needed to call it."
    )
    out.append(
        "- **`prismhr_call(method_id, args)`** — schema-validated invocation. "
        "Rejects missing required fields locally before hitting PrismHR. "
        "Blocks admin/internal services (`prismSecurity`, `subscription`, "
        "`signOn`, `system`) unconditionally. Requires the operation's scope."
    )
    out.append("")
    out.append(
        "Per-method metadata (empty-result conventions, mutation risk, typical "
        "companion calls) comes from a generated JSON produced by "
        "`scripts/generate_api_map.py` + a forthcoming Pydantic model factory."
    )
    out.append("")

    # ---- Explicit rejections ----
    out.append("## Explicit rejections")
    out.append("")
    out.append("### `POST /login/v1/requestAPIPermissions` is NOT exposed as a tool")
    out.append("")
    out.append(
        "PrismHR's `requestAPIPermissions` endpoint lets a web-service user "
        "file a request to widen their own API privileges (a human admin still "
        "has to approve). Surfacing this as an MCP tool would let Claude "
        "learn a pattern: *when a tool 403s, call the permission-widener and "
        "retry*. That breaks the trust boundary between the LLM and the "
        "system's access-control surface."
    )
    out.append("")
    out.append("If we ever expose it, the design must be:")
    out.append("")
    out.append("- Admin-scope-only (`admin:write`) — never granted by default.")
    out.append("- Two-step: `meta_draft_permission_request` → human review →")
    out.append("  `meta_submit_permission_request` with a one-time confirm token.")
    out.append("- Preview shows the exact diff (methods added, IPs added).")
    out.append("- Audit log entry for every draft + submit.")
    out.append("")
    out.append(
        "Until that design is built, the correct remediation for a 403 is to "
        "surface the error (handled — see `prismhr_error_message` in "
        "`clients/prismhr.py`) and let the human operator file the upgrade."
    )
    out.append("")

    target = pathlib.Path(".planning/prismhr-api-map.md")
    target.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {target} ({len(out)} lines, {target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
