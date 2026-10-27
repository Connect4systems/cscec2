"""Tender offers and conversion of submitted offers to Project Contracts."""
import frappe

from contractor.project_contract import commercial_creation_status, create_commercial_document, require_ready
from contractor.document_mapping import copy_child_values


@frappe.whitelist()
def creation_status(tender_analysis):
    return commercial_creation_status(tender_analysis, "Project Offer")


@frappe.whitelist()
def create_project_offer(tender_analysis):
    return create_commercial_document(tender_analysis, "Project Offer")


def get_submitted_offer(name):
    offer = frappe.get_doc("Project Offer", name)
    offer.check_permission("read")
    if offer.docstatus != 1:
        frappe.throw("Submit the Project Offer before creating a Project Contract")
    return offer


def validate_offer_source(contract):
    offer = get_submitted_offer(contract.project_offer)
    if (offer.tender_analysis != contract.tender_analysis or offer.company != contract.company
            or offer.customer != contract.customer or offer.currency != contract.currency):
        frappe.throw("Project Contract must match its submitted Project Offer's tender, company, customer, and currency")
    return offer


@frappe.whitelist()
def create_project_contract(project_offer):
    offer = get_submitted_offer(project_offer)
    tender = frappe.get_doc("Tender Analysis", offer.tender_analysis)
    tender.check_permission("read")
    require_ready(tender)
    existing = frappe.db.get_value("Project Contract",
        {"tender_analysis": offer.tender_analysis, "docstatus": ["<", 2]}, ["name", "project_offer"], as_dict=True)
    if existing:
        if existing.project_offer != offer.name:
            frappe.throw(f"Tender already has an active Project Contract: {existing.name}")
        frappe.get_doc("Project Contract", existing.name).check_permission("read")
        return {"existing": existing.name}
    doc = frappe.new_doc("Project Contract")
    doc.check_permission("create")
    excluded = {"status", "amended_from", "project_offer"}
    for field in doc.meta.fields:
        if field.fieldtype in ("Table", "Table MultiSelect", "Tab Break", "Section Break", "Column Break", "HTML", "Button", "Heading"):
            continue
        if field.fieldname not in excluded:
            doc.set(field.fieldname, offer.get(field.fieldname))
    doc.project_offer = offer.name
    doc.status = "Draft"
    doc.contractor_order = 1
    for table in ("clauses", "taxes", "deductions"):
        doc.set(table, [])
        for row in offer.get(table) or []:
            doc.append(table, copy_child_values(row))
    return {"doc": doc}
