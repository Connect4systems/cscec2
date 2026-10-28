"""Retire only app-owned, empty and unreferenced legacy definitions."""
import re

import frappe


RETIRED_DOCTYPES = (
    "E-Language", "Edu", "Deduction Table", "Project Engineer",
    "Purchase Category", "Type", "Workflow img",
)
RETAINED_DEPENDENCIES = {
    "Contractors table": "BOQ and Template BOQ subcontract costing",
    "Group Item": "Historical Projects, Costing Notes and certificates",
    "Clearence Item": "Historical customer certificate items",
    "Purchase Clearence Item": "Historical supplier certificate items",
    "Clearence Items Summary": "Historical certificate summaries",
    "Clearence Type": "Historical certificate item type links",
    "BOQ ID": "Item and Material Request Item customizations",
    "Project Item": "Historical item-based Project tables",
    "Project Contract Tax": "Historical tax migration",
    "Division": "Seeded classification master awaiting form integration",
    "Contract Type": "Active CR and Subcontractor Contract classification",
}


def configuration_references(doctype):
    """Look for literal references in site scripts and other text configuration."""
    literal = re.compile(r"(['\"`])" + re.escape(doctype) + r"\1")
    reasons = []
    for source, fields in (
        ("Client Script", ("script",)),
        ("Server Script", ("script",)),
        ("Print Format", ("html",)),
        ("Report", ("query", "javascript")),
        ("Workspace", ("content",)),
        ("Custom HTML Block", ("html", "script")),
    ):
        if not frappe.db.exists("DocType", source):
            continue
        meta = frappe.get_meta(source)
        for field in fields:
            if not meta.has_field(field):
                continue
            for row in frappe.get_all(source, filters={field: ["like", f"%{doctype}%"]},
                    fields=["name", field], limit_page_length=0):
                if literal.search(row.get(field) or ""):
                    reasons.append(f"{source}: {row.get('name')} ({field})")
    return reasons


def retirement_status(doctype):
    """Read only; keep definitions when site-specific usage cannot be ruled out."""
    info = frappe.db.get_value("DocType", doctype, ["module", "custom", "issingle"], as_dict=True)
    result = dict(doctype=doctype, exists=bool(info), removable=False, reasons=[])
    if not info:
        return result
    if info.get("module") != "Contractor App" or info.get("custom"):
        result["reasons"].append("Not an app-owned standard DocType")
        return result
    if info.get("issingle"):
        values = frappe.db.sql("select field, value from `tabSingles` where doctype=%s",
            doctype, as_dict=True)
        result["saved_single_values"] = sum(row.get("value") not in (None, "") for row in values)
        if result["saved_single_values"]:
            result["reasons"].append("Contains saved Single values")
    else:
        if not frappe.db.table_exists(doctype):
            result["reasons"].append("Table missing; requires manual inspection")
            return result
        result["record_count"] = frappe.db.count(doctype)
        if result["record_count"]:
            result["reasons"].append("Contains existing records")
    for source in ("DocField", "Custom Field"):
        parent_field = "parent" if source == "DocField" else "dt"
        references = frappe.get_all(source, filters={"options": doctype,
            "fieldtype": ["in", ["Link", "Table", "Table MultiSelect"]]},
            fields=[parent_field, "fieldname"])
        for row in references:
            if row.get(parent_field) != doctype:
                result["reasons"].append(f"{source}: {row.get(parent_field)}.{row.get('fieldname')}")
    for row in frappe.get_all("DocType Link", filters={"link_doctype": doctype}, fields=["parent"]):
        if row.parent != doctype:
            result["reasons"].append(f"Connection on {row.parent}")
    result["reasons"].extend(configuration_references(doctype))
    # A site may use these definitions in Workflow, Client Script, Print Format,
    # Dynamic Link or other records not shipped in this repository.
    from frappe.model.delete_doc import check_if_doc_is_linked, check_if_doc_is_dynamically_linked
    doc = frappe.get_doc("DocType", doctype)
    try:
        check_if_doc_is_linked(doc)
        check_if_doc_is_dynamically_linked(doc)
    except frappe.LinkExistsError as exc:
        result["reasons"].append(str(exc))
    result["removable"] = not result["reasons"]
    return result


def audit():
    """Bench read-only inventory, including site-only Texture candidates."""
    return dict(retired=[retirement_status(name) for name in RETIRED_DOCTYPES],
        retained_dependencies=RETAINED_DEPENDENCIES,
        texture_matches=frappe.get_all("DocType", filters={"name": ["like", "%Texture%"]},
            fields=["name", "module", "custom"]))


def retire_unused_doctypes():
    results = []
    for name in RETIRED_DOCTYPES:
        result = retirement_status(name)
        if result["removable"]:
            # No force, no SQL table drops, no deletion of business records.
            frappe.delete_doc("DocType", name)
            result["removed"] = True
        results.append(result)
    return results
