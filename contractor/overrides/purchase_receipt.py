import frappe
from frappe.model.naming import make_autoname
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt as ERPNextPurchaseReceipt

class CustomPurchaseReceipt(ERPNextPurchaseReceipt):
    def autoname(self):
        if not self.project:
            frappe.throw("Project is required for naming the Purchase Receipt.")

        abbreviation = frappe.db.get_value("Project", self.project, "custom_abbreviation")
        if not abbreviation:
            frappe.throw("custom_abbreviation is missing in the linked Project.")

        self.name = make_autoname(f"PRE-{abbreviation}-.####")

    def before_insert(self):
        if self.project:
            warehouse = frappe.db.get_value("Project", self.project, "custom_warehouse")
            if warehouse:
                for item in self.items:
                    item.warehouse = warehouse
