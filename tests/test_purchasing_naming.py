import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from test_tender_project_mapping import Record

ROOT = Path(__file__).parents[1]


class PurchasingNamingTest(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType('frappe')
        self.frappe.throw = MagicMock(side_effect=ValueError)
        self.frappe.db = MagicMock()
        self.frappe.db.get_value.return_value = ' ABC '
        naming = types.ModuleType('frappe.model.naming')
        self.autoname = naming.make_autoname = MagicMock(return_value='generated-number')
        po = types.ModuleType('erpnext.buying.doctype.purchase_order.purchase_order')
        receipt = types.ModuleType('erpnext.stock.doctype.purchase_receipt.purchase_receipt')
        class Native(Record):
            def before_insert(self):
                return 'native-before-insert'
            def after_insert(self):
                return 'native-after-insert'
        po.PurchaseOrder = receipt.PurchaseReceipt = Native
        self.modules = {'frappe': self.frappe, 'frappe.model.naming': naming,
            po.__name__: po, receipt.__name__: receipt}
        self.patcher = patch.dict(sys.modules, self.modules)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.helper = self.load('contractor.purchasing_naming', 'contractor/purchasing_naming.py')
        sys.modules['contractor.purchasing_naming'] = self.helper
        self.po = self.load('po_naming_test', 'contractor/overrides/purchase_order.py').CustomPurchaseOrder
        self.receipt = self.load('receipt_naming_test', 'contractor/overrides/purchase_receipt.py').CustomPurchaseReceipt

    def load(self, name, path):
        spec = importlib.util.spec_from_file_location(name, ROOT / path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_purchase_prefix_reads_project_without_order_type(self):
        for order_type, prefix in [('Purchase', 'PO'), ('Contract', 'PO'), (None, 'PO')]:
            doc = self.po(doctype='Purchase Order', project='PROJ-1', custom_type=order_type)
            doc.autoname()
            self.assertEqual(doc.name, 'generated-number')
            self.autoname.assert_called_with(f'{prefix}-ABC-.####')
        self.frappe.db.get_value.assert_called_with('Project', 'PROJ-1', 'custom_abbreviation')

    def test_receipt_prefix_and_other_native_methods_preserved(self):
        doc = self.receipt(doctype='Purchase Receipt', project='PROJ-1')
        doc.autoname()
        self.autoname.assert_called_with('PRE-ABC-.####')
        self.assertEqual(doc.before_insert(), 'native-before-insert')
        self.assertEqual(doc.after_insert(), 'native-after-insert')
        self.assertNotIn('before_insert', self.receipt.__dict__)
        self.assertNotIn('after_insert', self.po.__dict__)

    def test_missing_project_or_abbreviation_blocks_incomplete_name(self):
        for controller, doctype in [(self.po, 'Purchase Order'), (self.receipt, 'Purchase Receipt')]:
            with self.assertRaises(ValueError):
                controller(doctype=doctype, project=None).autoname()
            self.frappe.db.get_value.return_value = '   '
            with self.assertRaises(ValueError):
                controller(doctype=doctype, project='PROJ-1').autoname()
        self.autoname.assert_not_called()
