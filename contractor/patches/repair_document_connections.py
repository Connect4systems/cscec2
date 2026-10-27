"""Refresh dashboard metadata and repair safe, unambiguous BOQ row references."""
import frappe
from frappe.utils import now


def execute():
    for doctype in ("Costing Note", "BOQ", "Project Offer", "Project Contract"):
        frappe.reload_doc("contractor_app", "doctype", doctype.lower().replace(" ", "_"), force=True)
        frappe.db.set_value("DocType", doctype, "modified", now(), update_modified=False)
        frappe.clear_cache(doctype=doctype)
    from contractor.tender_pricing import sync_boq_reference
    for name in frappe.get_all("BOQ", filters={"docstatus": ["<", 2]}, pluck="name",
            order_by="docstatus asc, modified asc"):
        boq = frappe.get_doc("BOQ", name)
        if boq.line_id:
            row = frappe.db.get_value("Costing Note Items", boq.line_id, ["parent", "parenttype"], as_dict=True)
            if row and row.parenttype == "Costing Note" and not boq.costing_note:
                boq.costing_note = row.parent
                frappe.db.set_value("BOQ", boq.name, "costing_note", row.parent, update_modified=False)
        elif boq.costing_note and boq.contractual_clause:
            rows = frappe.get_all("Costing Note Items", filters={"parent": boq.costing_note,
                "parenttype": "Costing Note", "contractual_clause": boq.contractual_clause, "is_group": 0}, pluck="name")
            if len(rows) == 1:
                boq.line_id = rows[0]
                frappe.db.set_value("BOQ", boq.name, "line_id", rows[0], update_modified=False)
        if boq.costing_note and boq.line_id and frappe.db.exists("Costing Note Items",
                {"name": boq.line_id, "parent": boq.costing_note, "parenttype": "Costing Note"}):
            sync_boq_reference(boq)
