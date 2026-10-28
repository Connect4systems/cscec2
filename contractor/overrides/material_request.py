import frappe
from frappe.model.naming import make_autoname

# Import ERPNext base class and function
from erpnext.stock.doctype.material_request.material_request import MaterialRequest as ERPNextMaterialRequest
from erpnext.stock.doctype.material_request.material_request import make_purchase_order as erp_make_po

class CustomMaterialRequest(ERPNextMaterialRequest):
    def autoname(self):
        if not self.custom_project_abbriviation or not self.material_request_type:
            frappe.throw("Both 'Project Abbreviation' and 'Material Request Type' must be set.")

        if self.material_request_type == "Purchase":
            prefix = "PR"
        elif self.material_request_type == "Customer Provided":
            prefix = "CP"
        elif self.material_request_type == "Material Transfer":
            prefix = "TR"
        else:
            prefix = "MR"

        self.name = make_autoname(f"{prefix}-{self.custom_project_abbriviation}-.####")


@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None):
    """Use ERPNext's native mapping without adding Purchase Order fields."""
    return erp_make_po(source_name, target_doc)
