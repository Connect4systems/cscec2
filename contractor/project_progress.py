"""Submitted customer and supplier certificates drive separate progress streams."""
import frappe

from contractor.progress_rules import update_quantities


CERTIFICATES = ("Project Clearnce", "Subcontract Clearnce")


def executed_quantities(project, doctype, exclude=None, supplier=None):
    if doctype not in CERTIFICATES:
        raise ValueError("Unsupported certificate type")
    filters = {"project": project, "docstatus": 1, "legacy_record": 0}
    if exclude:
        filters["name"] = ["!=", exclude]
    if supplier:
        filters["supplier"] = supplier
    parents = frappe.get_all(doctype, filters=filters, pluck="name")
    result = {}
    if parents:
        for row in frappe.get_all("Clearnce Clause", filters={"parent": ["in", parents], "parenttype": doctype,
                "is_group": 0}, fields=["project_clause_ref", "qty"]):
            result[row.project_clause_ref] = result.get(row.project_clause_ref, 0) + float(row.qty or 0)
    return result


def validate_project(doc, method=None):
    if not doc.get("project_contract"):
        return
    summary = update_quantities(doc.project_clauses,
        executed_quantities(doc.name, CERTIFICATES[0]), executed_quantities(doc.name, CERTIFICATES[1]))
    doc.set("project_clause_groups", summary)


def refresh_project(project):
    frappe.db.sql("select name from `tabProject` where name=%s for update", project)
    doc = frappe.get_doc("Project", project)
    if not doc.get("project_contract"):
        return
    validate_project(doc)
    fields = ("completed_qty", "remaining_qty", "completion_percentage", "subcontract_completed_qty",
        "subcontract_remaining_qty", "subcontract_completion_percentage")
    for row in doc.project_clauses:
        frappe.db.set_value("Project Clause", row.name, {field: row.get(field) for field in fields}, update_modified=False)
    frappe.db.delete("Project Clause Summary", {"parent": doc.name, "parenttype": "Project", "parentfield": "project_clause_groups"})
    from frappe.model.naming import set_new_name
    for row in doc.project_clause_groups:
        set_new_name(row)
        row.db_insert()
