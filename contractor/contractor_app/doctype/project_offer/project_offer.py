import frappe

from contractor.contractor_app.doctype.project_contract.project_contract import ProjectContract


class ProjectOffer(ProjectContract):
    def before_cancel(self):
        existing = frappe.db.get_value("Project Contract",
            {"project_offer": self.name, "docstatus": ["<", 2]}, "name")
        if existing:
            frappe.throw(f"Cancel or delete the linked Project Contract first: {existing}")
