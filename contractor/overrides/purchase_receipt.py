from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt

from contractor.purchasing_naming import project_name


class CustomPurchaseReceipt(PurchaseReceipt):
    def autoname(self):
        self.name = project_name(self, 'PRE')
