"""Accounting-system adapters (Intacct + future Sage, QBO, NetSuite).

Each adapter exposes a narrow surface matched to the reconciliation
workflows in simploy.workflows. Live credentials live in 1Password and
are loaded via the same pattern as PrismHRClient (no in-tree secrets).
"""
