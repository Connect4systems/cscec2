import frappe
from frappe.model.naming import make_autoname
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder as ERPNextPurchaseOrder

class CustomPurchaseOrder(ERPNextPurchaseOrder):
    def autoname(self):
        if not self.custom_project_abbriviation or not self.custom_type:
            frappe.throw("Both 'custom_project_abbriviation' and 'custom_type' must be set.")

        prefix = "PO"
        if self.custom_type == "Contract":
            prefix = "CO"

        self.name = make_autoname(f"{prefix}-{self.custom_project_abbriviation}-.####")

    def after_insert(self):
        if self.custom_comparison:
            try:
                frappe.db.set_value("Comparison", self.custom_comparison, "purchase_order", self.name)
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(f"Failed to update Comparison with PO: {str(e)}")
