"""Create the operational Project and clause snapshot from a submitted contract."""
import frappe

from contractor.document_mapping import copy_child_values


@frappe.whitelist()
def create_project(project_contract):
    frappe.db.sql("select name from `tabProject Contract` where name=%s for update", project_contract)
    contract = frappe.get_doc("Project Contract", project_contract)
    contract.check_permission("read")
    if contract.docstatus != 1:
        frappe.throw("Submit the Project Contract before creating a Project")
    existing = contract.get("created_project") or frappe.db.get_value("Project", {"project_contract": contract.name}, "name")
    if existing:
        project = frappe.get_doc("Project", existing)
        project.check_permission("read")
        if project.get("project_contract") != contract.name:
            frappe.throw("The created Project does not belong to this Project Contract")
        frappe.db.set_value("Project Contract", contract.name, "created_project", project.name, update_modified=False)
        return {"project": project.name}
    project_name = str(contract.get("project") or "").strip()
    if not project_name:
        frappe.throw("Enter the Project name on the Project Contract first")
    if frappe.db.exists("Project", {"project_name": project_name}):
        frappe.throw("This Project name is already used by another Project; enter a unique name")
    project = frappe.new_doc("Project")
    project.check_permission("create")
    project.update(dict(project_name=project_name, company=contract.company, customer=contract.customer,
        expected_start_date=contract.transaction_date, expected_end_date=contract.delivery_date,
        status="Open", is_active="Yes", project_contract=contract.name,
        project_offer=contract.get("project_offer"), tender_analysis=contract.tender_analysis,
        project_contract_currency=contract.currency, project_contract_total=contract.grand_total))
    if not project.get("naming_series"):
        project.naming_series = "PROJ-.####"
    for row in contract.clauses:
        project.append("project_clauses", copy_child_values(row))
    project.insert()
    frappe.db.set_value("Project Contract", contract.name, "created_project", project.name, update_modified=False)
    return {"project": project.name}
