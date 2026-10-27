"""Creation and readiness checks for clause-based Project Contracts."""
import frappe
from frappe.utils import today

from contractor.project_contract_rules import require_submitted_costing


def require_ready(tender):
    notes = frappe.get_all("Costing Note", filters={"tender_analysis": tender.name, "docstatus": ["<", 2]},
        fields=["name", "docstatus"])
    try:
        require_submitted_costing(tender.clauses, notes)
    except ValueError as exc:
        frappe.throw(str(exc))


@frappe.whitelist()
def creation_status(tender_analysis):
    tender = frappe.get_doc("Tender Analysis", tender_analysis)
    tender.check_permission("read")
    if not frappe.has_permission("Project Contract", "create"):
        return {"ready": False}
    notes = frappe.get_all("Costing Note", filters={"tender_analysis": tender.name, "docstatus": ["<", 2]},
        fields=["name", "docstatus"])
    try:
        require_submitted_costing(tender.clauses, notes)
    except ValueError as exc:
        return {"ready": False, "reason": str(exc)}
    existing = frappe.db.get_value("Project Contract", {"tender_analysis": tender.name, "docstatus": ["<", 2]}, "name")
    return {"ready": not bool(existing)}


@frappe.whitelist()
def create_project_contract(tender_analysis):
    tender = frappe.get_doc("Tender Analysis", tender_analysis)
    tender.check_permission("read")
    require_ready(tender)
    existing = frappe.db.get_value("Project Contract", {"tender_analysis": tender.name, "docstatus": ["<", 2]}, "name")
    if existing:
        frappe.get_doc("Project Contract", existing).check_permission("read")
        return {"existing": existing}
    doc = frappe.new_doc("Project Contract")
    doc.check_permission("create")
    from contractor.tender_pricing import submitted_boq_links
    boqs = submitted_boq_links(tender)
    base_currency = frappe.get_cached_value("Company", tender.company, "default_currency")
    doc.update(dict(title=tender.title, tender_analysis=tender.name, tender_number=tender.tender_number,
        company=tender.company, currency=tender.currency, contractor_order=1,
        customer=tender.party_name if tender.party_type == "Customer" else None,
        transaction_date=today(), delivery_date=today(),
        conversion_rate=1 if base_currency == tender.currency else 0))
    for row in tender.clauses:
        doc.append("clauses", dict(is_group=row.is_group, series_number=row.series_number,
            parent_series=row.parent_series, clause_title=row.clause_title, source_row=row.name,
            contractual_clause=row.contractual_clause, qty=row.qty, uom=row.uom,
            rate=row.rate, amount=row.amount, costing_note=row.applied_costing_note,
            submitted_boq=boqs.get(row.name), delivery_date=doc.delivery_date))
    return {"doc": doc}
