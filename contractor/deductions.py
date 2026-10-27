"""Shared deduction templates and validation for the tender-to-contract flow."""
import frappe

from contractor.document_mapping import copy_child_values
from contractor.project_contract_rules import apply_deductions


@frappe.whitelist()
def get_selling_deductions(template, company):
    doc = frappe.get_doc("Selling Deductions Template", template)
    doc.check_permission("read")
    validate_accounts(doc.deductions, company)
    return [copy_child_values(row) for row in doc.deductions]


def validate_accounts(rows, company):
    for row in rows:
        account = row.get("account")
        if account and frappe.get_cached_value("Account", account, "company") != company:
            frappe.throw("Deduction accounts must belong to the document company")


def update_tender_deductions(doc):
    if doc.get("selling_deductions_template"):
        template = frappe.get_doc("Selling Deductions Template", doc.selling_deductions_template)
        template.check_permission("read")
        old = doc.get_doc_before_save()
        changed = not old or old.get("selling_deductions_template") != doc.selling_deductions_template
        if changed and not doc.get("deductions"):
            doc.set("deductions", [copy_child_values(row) for row in template.deductions])
    rows = doc.get("deductions") or []
    validate_accounts(rows, doc.company)
    try:
        values = apply_deductions(rows, doc.total_amount)
    except ValueError as exc:
        frappe.throw(str(exc))
    doc.total_deductions = values["total_deductions"]
    doc.net_payable = values["net_payable"]
