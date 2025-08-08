import frappe
from frappe.model.naming import make_autoname

# Import ERPNext base class and function
from erpnext.stock.doctype.material_request.material_request import MaterialRequest as ERPNextMaterialRequest
from erpnext.stock.doctype.material_request.material_request import make_purchase_order as erp_make_po
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder

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
    def set_missing_values(source, target):
        # Copy custom_project into project field of Purchase Order
        if source.custom_project:
            target.project = source.custom_project

        # Optional: set PO type if needed (e.g., "Purchase" or custom)
        if source.material_request_type:
            target.custom_type = source.material_request_type  # Only if you have a custom_type field in PO

    return erp_make_po(source_name, target_doc, postprocess=set_missing_values)
