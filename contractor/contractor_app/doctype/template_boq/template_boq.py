import frappe
from frappe.model.document import Document


class TemplateBOQ(Document):
    def validate(self):
        from contractor.boq_quantities import calculate_resources
        try:
            calculate_resources(self)
        except ValueError as exc:
            frappe.throw(str(exc))
