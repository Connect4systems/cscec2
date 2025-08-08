import frappe
from frappe.model.naming import make_autoname
from frappe.model.document import Document

class CustomSubcontractorCustody(Document):
    def autoname(self):
        if not self.project:
            frappe.throw("Project is required for naming.")

        project_abbr = frappe.db.get_value("Project", self.project, "custom_abbreviation")
        if not project_abbr:
            frappe.throw("Project abbreviation is missing in the selected Project.")

        self.name = make_autoname(f"SC-{project_abbr}-.####")

    def on_submit(self):
        self.create_stock_entry()

    def create_stock_entry(self):
        if not self.project or not self.subcontractor:
            frappe.throw("Project and Subcontractor are required to create Stock Entry.")

        project_doc = frappe.get_doc("Project", self.project)
        warehouse = project_doc.get("custom_warehouse")
        if not warehouse:
            frappe.throw("Custom Warehouse not defined in Project.")

        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Transfer"
        se.project = self.project
        se.subcontractor = self.subcontractor

        if self.type == "Out":
            se.from_warehouse = warehouse
            se.to_warehouse = "Subcontractor - C"
        elif self.type == "Return":
            se.from_warehouse = "Subcontractor - C"
            se.to_warehouse = warehouse
        else:
            frappe.throw("Invalid type. Must be 'Out' or 'Return'.")

        for item in self.items:
            se.append("items", {
                "item_code": item.item,  # ✅ fixed field name
                "qty": item.qty,
                "uom": item.uom,
                "stock_uom": item.uom,
                "conversion_factor": 1,
                "s_warehouse": se.from_warehouse,
                "t_warehouse": se.to_warehouse,
                "to_subcontractor": self.subcontractor if self.type == "Out" else None,
                "subcontractor": self.subcontractor if self.type == "Return" else None
            })

        se.insert(ignore_permissions=True)
        se.submit()

        # Optional: link back to custody if you add a link field
        # self.db_set("stock_entry", se.name)

        frappe.msgprint(f"Stock Entry <b>{se.name}</b> created and submitted.")
