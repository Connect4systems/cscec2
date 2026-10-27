"""Repair skipped metadata imports and missing project text on existing documents."""
import json

import frappe
from frappe.utils import now


def execute():
    doctypes = ("Tender Analysis", "Costing Note", "BOQ", "Project Offer", "Project Contract")
    # Site-edited metadata may have newer timestamps than the source JSON.
    for doctype in doctypes + ("Project Clause",):
        frappe.reload_doc("contractor_app", "doctype", doctype.lower().replace(" ", "_"), force=True)
    for doctype in doctypes:
        for setter in frappe.get_all("Property Setter", filters={"doc_type": doctype,
                "field_name": "project", "property": ["in", ["fieldtype", "options", "hidden", "depends_on",
                    "read_only", "read_only_depends_on", "allow_on_submit"]]}, pluck="name"):
            frappe.delete_doc("Property Setter", setter)
        for setter in frappe.get_all("Property Setter", filters={"doc_type": doctype, "property": "field_order"},
                fields=["name", "value"]):
            try:
                order = json.loads(setter.value)
            except (TypeError, ValueError):
                continue
            if not isinstance(order, list):
                continue
            required = ["project"] + (["created_project"] if doctype == "Project Contract" else [])
            for field in required:
                if field not in order:
                    position = order.index("tender_number") + 1 if "tender_number" in order else 0
                    order.insert(position, field)
            frappe.db.set_value("Property Setter", setter.name, "value", json.dumps(order))
        frappe.db.set_value("DocType", doctype, "modified", now(), update_modified=False)
        frappe.clear_cache(doctype=doctype)
    from contractor.project_names import fill_project_name
    for doctype in doctypes[1:]:
        for name in frappe.get_all(doctype, pluck="name"):
            doc = frappe.get_doc(doctype, name)
            if str(doc.get("project") or "").strip():
                continue
            if fill_project_name(doc):
                frappe.db.set_value(doctype, name, "project", doc.project, update_modified=False)
