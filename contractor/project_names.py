"""Fill missing project text from the document's source, preserving manual edits."""
import frappe


def fill_project_name(doc):
    if str(doc.get("project") or "").strip():
        return doc.get("project")
    sources = []
    if doc.get("doctype") == "Project Contract" and doc.get("created_project"):
        sources.append(("Project", doc.created_project, "project_name"))
    if doc.get("doctype") == "BOQ" and doc.get("costing_note"):
        sources.append(("Costing Note", doc.costing_note, "project"))
    if doc.get("doctype") == "Project Contract" and doc.get("project_offer"):
        sources.append(("Project Offer", doc.project_offer, "project"))
    if doc.get("tender_analysis"):
        sources.append(("Tender Analysis", doc.tender_analysis, "project"))
    if doc.get("doctype") == "Costing Note" and doc.get("source_project"):
        sources.append(("Project", doc.source_project, "project_name"))
    for doctype, name, field in sources:
        source = frappe.get_doc(doctype, name)
        source.check_permission("read")
        value = source.get(field)
        if field == "project" and not str(value or "").strip():
            value = fill_project_name(source)
        if str(value or "").strip():
            doc.project = value
            return value
    return None


@frappe.whitelist()
def get_project_name(doctype, name):
    if doctype not in ("Costing Note", "BOQ", "Project Offer", "Project Contract"):
        frappe.throw("Unsupported project-name source")
    doc = frappe.get_doc(doctype, name)
    doc.check_permission("read")
    return fill_project_name(doc)
