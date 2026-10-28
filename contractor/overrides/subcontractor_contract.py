import frappe
from frappe.model.naming import make_autoname
from contractor.contractor_app.doctype.subcontractor_contract.subcontractor_contract import SubcontractorContract

class CustomSubcontractorContract(SubcontractorContract):
    def autoname(self):
        if not self.project:
            frappe.throw("Project is required for naming Subcontractor Contract.")

        # âœ… fetch abbreviation dynamically from Project
        abbr = frappe.db.get_value("Project", self.project, "custom_abbreviation")
        if not abbr:
            frappe.throw("Project abbreviation (custom_abbreviation) is missing in the selected Project.")

        self.name = make_autoname(f"SCC-{abbr}-.####")
