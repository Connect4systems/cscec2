"""Use ERPNext's Sales Order tax engine for clause-based commercial documents.

The Sales Order is an unsaved calculation context only. Clause headings are
excluded, and clause references are item names, never stock Item references.
"""
import math

import frappe
from frappe.utils import flt

from contractor.project_contract_rules import apply_deductions


TOTAL_FIELDS = (
    "total_qty", "total", "base_total", "net_total", "base_net_total",
    "discount_amount", "base_discount_amount", "total_taxes_and_charges",
    "base_total_taxes_and_charges", "grand_total", "base_grand_total",
    "rounded_total", "base_rounded_total", "rounding_adjustment", "base_rounding_adjustment",
)
CLAUSE_AMOUNT_FIELDS = ("amount", "base_amount", "net_rate", "net_amount", "base_net_rate", "base_net_amount")
IDENTITY_FIELDS = {"name", "doctype", "parent", "parentfield", "parenttype", "idx", "docstatus", "owner", "creation", "modified", "modified_by"}


def tax_values(row):
    return {key: value for key, value in row.as_dict().items()
        if key not in IDENTITY_FIELDS and not key.startswith("_")}


def validate_template(name, company):
    template = frappe.get_doc("Sales Taxes and Charges Template", name)
    template.check_permission("read")
    if template.company != company or template.disabled:
        frappe.throw("Select an enabled Sales Taxes and Charges Template for the contract company")
    return template


@frappe.whitelist()
def get_sales_tax_template(template, company):
    validate_template(template, company)
    from erpnext.controllers.accounts_controller import get_taxes_and_charges
    return get_taxes_and_charges("Sales Taxes and Charges Template", template)


def calculate_contract_taxes(doc):
    from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals

    if doc.get("taxes_and_charges"):
        validate_template(doc.taxes_and_charges, doc.company)
    proxy = frappe.new_doc("Sales Order")
    for field in ("company", "currency", "conversion_rate", "customer", "transaction_date",
            "tax_category", "taxes_and_charges", "discount_amount", "additional_discount_percentage",
            "disable_rounded_total"):
        proxy.set(field, doc.get(field))
    proxy.apply_discount_on = doc.get("apply_discount_on") or "Net Total"
    proxy.ignore_pricing_rule = 1
    proxy._action = "save"
    proxy.set("items", [])
    details = []
    for row in doc.clauses:
        if row.is_group:
            continue
        qty, rate = flt(row.qty), flt(row.rate)
        if not math.isfinite(qty) or qty <= 0 or not math.isfinite(rate) or rate < 0:
            frappe.throw("Clause quantities must be positive and rates must be nonnegative finite numbers")
        details.append(row)
        proxy.append("items", dict(item_code=None, item_name=row.contractual_clause or row.source_row,
            description=row.clause_title, qty=qty, rate=rate, uom=row.uom,
            stock_uom=row.uom, conversion_factor=1, stock_qty=qty,
            item_tax_template=None, item_tax_rate="{}", discount_percentage=0,
            discount_amount=0, price_list_rate=0, margin_rate_or_amount=0))
    proxy.set("taxes", [])
    for row in doc.taxes:
        proxy.append("taxes", tax_values(row))
    # All native charge types, included taxes, discounts, precision, and rounding
    # are handled by the installed ERPNext version, without saving the proxy.
    calculate_taxes_and_totals(proxy)
    for field in TOTAL_FIELDS:
        doc.set(field, proxy.get(field) or 0)
    doc.conversion_rate = proxy.conversion_rate
    for row, result in zip(details, proxy.items):
        for field in CLAUSE_AMOUNT_FIELDS:
            row.set(field, result.get(field) or 0)
    group = None
    for row in doc.clauses:
        if row.is_group:
            group = row
            row.rate = 0
            for field in CLAUSE_AMOUNT_FIELDS:
                row.set(field, 0)
        elif group is not None:
            for field in ("amount", "base_amount", "net_amount", "base_net_amount"):
                group.set(field, flt(group.get(field)) + flt(row.get(field)))
    for row, result in zip(doc.taxes, proxy.taxes):
        row.update(tax_values(result))
    try:
        doc.update(apply_deductions(doc.deductions, doc.grand_total, doc.conversion_rate))
    except ValueError as exc:
        frappe.throw(str(exc))


@frappe.whitelist()
def preview_totals(doc):
    data = frappe.parse_json(doc)
    if data.get("doctype") not in ("Project Contract", "Project Offer"):
        frappe.throw("Expected a Project Contract or Project Offer")
    candidate = frappe.get_doc(data)
    if not candidate.is_new():
        frappe.get_doc(candidate.doctype, candidate.name).check_permission("write")
    else:
        candidate.check_permission("create")
    if candidate.docstatus != 0:
        frappe.throw("Only draft contract totals can be recalculated")
    calculate_contract_taxes(candidate)
    return dict(totals={field: candidate.get(field) for field in TOTAL_FIELDS + (
        "conversion_rate", "total_deductions", "base_total_deductions", "net_payable")},
        clauses=[{field: row.get(field) for field in CLAUSE_AMOUNT_FIELDS} for row in candidate.clauses],
        taxes=[tax_values(row) for row in candidate.taxes],
        deductions=[dict(value=row.value) for row in candidate.deductions])
