"""Populate navigation fields for existing tender BOQs without repricing."""
import frappe


def execute():
    from contractor.tender_pricing import sync_boq_reference

    for boq in frappe.get_all("BOQ", filters={"tender_analysis": ["is", "set"]}, pluck="name"):
        doc = frappe.get_doc("BOQ", boq)
        if doc.contractual_clause:
            title = frappe.db.get_value("Contractual Clause", doc.contractual_clause, "title")
            frappe.db.set_value("BOQ", doc.name, "clause_title", title, update_modified=False)
        if doc.docstatus < 2 and doc.costing_note and doc.line_id:
            if frappe.db.exists("Costing Note Items", {"name": doc.line_id, "parent": doc.costing_note}):
                sync_boq_reference(doc)
