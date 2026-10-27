"""Preserve legacy Project IDs separately and display names in new Data fields."""
import frappe


def execute():
    for doctype in ("Costing Note", "BOQ", "Project Offer", "Project Contract"):
        fields = ["name", "project"] + (["tender_analysis", "source_project"] if doctype == "Costing Note" else [])
        for doc in frappe.get_all(doctype, filters={"project": ["is", "set"]}, fields=fields):
            name = frappe.db.get_value("Project", doc.project, "project_name")
            if not name:
                continue
            values = {"project": name}
            if doctype == "Costing Note" and not doc.tender_analysis and not doc.source_project:
                values["source_project"] = doc.project
            frappe.db.set_value(doctype, doc.name, values, update_modified=False)
