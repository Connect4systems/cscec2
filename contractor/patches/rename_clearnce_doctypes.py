"""Rename parent DocTypes in place, preserving child rows, links and ledger history."""
import frappe


def execute():
    pairs = (("Clearence", "Project Clearnce"), ("Purchase Clearence", "Subcontract Clearnce"))
    # Preflight every target before the first DDL rename (which commits in Frappe).
    for old, new in pairs:
        if frappe.db.exists("DocType", old) and frappe.db.exists("DocType", new):
            frappe.throw(f"Both {old} and {new} exist. Reconcile them before migration; no data was merged.")
    for old, new in pairs:
        if not frappe.db.exists("DocType", old):
            continue
        if not frappe.db.has_column(old, "legacy_record"):
            frappe.db.sql(f"alter table `tab{old}` add column `legacy_record` int not null default 0")
        frappe.db.sql(f"update `tab{old}` set legacy_record=1")
        frappe.rename_doc("DocType", old, new, force=True, ignore_permissions=True, show_alert=False)
