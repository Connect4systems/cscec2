"""Upgrade existing project snapshots and retire app-owned purchasing changes."""
import json
from pathlib import Path
import frappe
from frappe.utils import now


def execute():
    for slug in ("project_clause", "project_clause_summary", "clearnce_clause", "project_clearnce", "subcontract_clearnce"):
        frappe.reload_doc("contractor_app", "doctype", slug, force=True)
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    root = Path(__file__).parents[1]
    fields = json.loads((root / "fixtures/custom_field.json").read_text(encoding="utf-8"))
    create_custom_fields({"Project": [{k: v for k, v in row.items() if k not in ("doctype", "dt", "name")}
        for row in fields if row.get("dt") == "Project"]}, update=True)
    old = frappe.db.get_value("Custom Field", {"dt": "Project", "fieldname": "project_contract_total"}, "name")
    if old:
        frappe.delete_doc("Custom Field", old)
    for setter in frappe.get_all("Property Setter", filters={"doc_type": "Project", "property": "field_order"},
            fields=["name", "value"]):
        try:
            order = json.loads(setter.value)
        except (TypeError, ValueError):
            continue
        if not isinstance(order, list):
            continue
        order = [field for field in order if field not in ("project_contract_total", "project_clause_groups")]
        position = order.index("project_clauses") if "project_clauses" in order else len(order)
        order.insert(position, "project_clause_groups")
        frappe.db.set_value("Property Setter", setter.name, "value", json.dumps(order))
    data = json.loads((Path(__file__).with_name("retired_purchasing.json")).read_text())
    for field in data["fields"]:
        name = frappe.db.get_value("Custom Field", field, "name")
        if name:
            frappe.db.set_value("Custom Field", name, {"hidden": 1, "in_list_view": 0, "reqd": 0})
    for name in data["setters"]:
        if frappe.db.exists("Property Setter", name):
            frappe.delete_doc("Property Setter", name)
    for name in data.get("links", []):
        frappe.db.delete("DocType Link", {"name": name})
    for module, doctype in (("buying", "purchase_order"), ("buying", "purchase_order_item"),
            ("accounts", "purchase_invoice"), ("accounts", "purchase_invoice_item"),
            ("accounts", "purchase_taxes_and_charges")):
        frappe.reload_doc(module, "doctype", doctype, force=True)
        name = "Purchase Taxes and Charges" if doctype == "purchase_taxes_and_charges" else doctype.replace("_", " ").title()
        frappe.db.set_value("DocType", name, "modified", now(), update_modified=False)
    from contractor.project_progress import refresh_project
    for name in frappe.get_all("Project", filters={"project_contract": ["is", "set"]}, pluck="name"):
        doc = frappe.get_doc("Project", name)
        contract = frappe.get_doc("Project Contract", doc.project_contract)
        for row in doc.project_clauses:
            matches = [source for source in contract.clauses if source.source_row == row.source_row
                and source.contractual_clause == row.contractual_clause]
            if len(matches) == 1:
                frappe.db.set_value("Project Clause", row.name, "contract_clause_row", matches[0].name, update_modified=False)
        refresh_project(name)
    frappe.db.set_value("DocType", "Project", "modified", now(), update_modified=False)
    frappe.clear_cache()
