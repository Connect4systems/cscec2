import frappe
from frappe.model.naming import make_autoname
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry as ERPNextStockEntry

class CustomStockEntry(ERPNextStockEntry):
    def autoname(self):
        if not self.custom_project_abbriviation or not self.stock_entry_type:
            frappe.throw("Both 'custom_project_abbriviation' and 'stock_entry_type' must be set.")

        prefix_map = {
            "Material Issue": "MI",
            "Material Receipt": "MR",
            "Material Transfer": "MT"
        }

        prefix = prefix_map.get(self.stock_entry_type, "SE")  # Default fallback
        self.name = make_autoname(f"{prefix}-{self.custom_project_abbriviation}-.####")

    def before_insert(self):
        # Auto-fetch Source Warehouse from Project → custom_warehouse
        if self.project:
            warehouse = frappe.db.get_value("Project", self.project, "custom_warehouse")
            if warehouse:
                if self.stock_entry_type in ["Material Issue", "Material Transfer"]:
                    self.from_warehouse = warehouse
                elif self.stock_entry_type == "Material Receipt":
                    self.to_warehouse = warehouse
