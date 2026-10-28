from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder

from contractor.purchasing_naming import project_name


class CustomPurchaseOrder(PurchaseOrder):
    def autoname(self):
        self.name = project_name(self, 'PO')
