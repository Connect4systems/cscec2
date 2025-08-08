import frappe
from frappe.model.naming import make_autoname
from frappe.model.document import Document

class CustomCR(Document):
    def autoname(self):
        if not self.project:
            frappe.throw("Project is required for naming CR.")

        abbreviation = frappe.db.get_value("Project", self.project, "custom_abbreviation")
        if not abbreviation:
            frappe.throw("custom_abbreviation is missing in the linked Project.")

        self.name = make_autoname(f"CR-{abbreviation}-.####")
