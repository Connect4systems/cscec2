"""Exercise the native-tax adapter with a controlled ERPNext boundary."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class Record:
    def __init__(self, **values):
        self.__dict__.update(values)

    def get(self, field, default=None):
        return getattr(self, field, default)

    def set(self, field, value):
        setattr(self, field, value)

    def update(self, values):
        self.__dict__.update(values)

    def as_dict(self):
        return dict(self.__dict__)

    def append(self, field, values):
        row = Record(**values)
        getattr(self, field).append(row)
        return row


class NativeTaxAdapterTest(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType('frappe')
        fake.whitelist = lambda: lambda fn: fn
        fake.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
        self.proxy = Record(doctype='Sales Order')
        fake.new_doc = MagicMock(return_value=self.proxy)
        utils = types.ModuleType('frappe.utils')
        utils.flt = lambda value: float(value or 0)
        engine = types.ModuleType('erpnext.controllers.taxes_and_totals')
        self.engine = MagicMock(side_effect=self.native_calculation)
        engine.calculate_taxes_and_totals = self.engine
        self.modules = {'frappe': fake, 'frappe.utils': utils, 'erpnext.controllers.taxes_and_totals': engine}
        spec = importlib.util.spec_from_file_location('contract_taxes_under_test',
            Path(__file__).parents[1] / 'contractor/project_contract_taxes.py')
        self.service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, self.modules):
            spec.loader.exec_module(self.service)
        self.doc = Record(company='Company', currency='EGP', conversion_rate=1, customer='Customer',
            clauses=[Record(is_group=1, qty=999, rate=999),
                Record(is_group=0, contractual_clause='CC-1', clause_title='Concrete', source_row='source', qty=1, rate=110, uom='Nos')],
            taxes=[Record(name='tax-1', parent='PC-1', charge_type='On Net Total', account_head='VAT',
                included_in_print_rate=1, row_id=None, rate=10)],
            deductions=[Record(title='Retention', percent=5)])

    def native_calculation(self, doc):
        # The adapter must pass native tax flags through and accept native totals.
        for field in self.service.TOTAL_FIELDS:
            doc.set(field, 0)
        doc.update(dict(total_qty=1, total=110, net_total=100, total_taxes_and_charges=10,
            grand_total=110, base_grand_total=110, rounded_total=110))
        for item in doc.items:
            item.update(dict(amount=110, net_amount=100, net_rate=100, base_amount=110, base_net_rate=100, base_net_amount=100))
        doc.taxes[0].tax_amount = 10

    def test_native_engine_receives_only_details_without_stock_item_references(self):
        with patch.dict(sys.modules, self.modules):
            self.service.calculate_contract_taxes(self.doc)
        self.engine.assert_called_once_with(self.proxy)
        self.assertEqual(self.proxy.doctype, 'Sales Order')
        self.assertEqual(len(self.proxy.items), 1)
        self.assertIsNone(self.proxy.items[0].item_code)
        self.assertEqual(self.proxy.items[0].item_name, 'CC-1')
        self.assertEqual(self.proxy.taxes[0].included_in_print_rate, 1)
        self.assertFalse(hasattr(self.proxy.taxes[0], 'parent'))
        self.assertEqual(self.doc.net_total, 100)
        self.assertEqual(self.doc.clauses[0].amount, 110)
        self.assertEqual(self.doc.clauses[0].net_amount, 100)
        self.assertEqual(self.doc.deductions[0].title, 'Retention')
        self.assertEqual(self.doc.net_payable, 104.5)

    def test_previous_row_tax_flags_are_passed_through_unchanged(self):
        self.doc.taxes[0].charge_type = 'On Previous Row Total'
        self.doc.taxes[0].row_id = '1'
        with patch.dict(sys.modules, self.modules):
            self.service.calculate_contract_taxes(self.doc)
        self.assertEqual(self.proxy.taxes[0].charge_type, 'On Previous Row Total')
        self.assertEqual(self.proxy.taxes[0].row_id, '1')

    def test_invalid_detail_quantity_is_rejected_before_calculation(self):
        self.doc.clauses[1].qty = 0
        with patch.dict(sys.modules, self.modules):
            with self.assertRaisesRegex(ValueError, 'quantities must be positive'):
                self.service.calculate_contract_taxes(self.doc)
        self.engine.assert_not_called()

    def test_subcontract_certificate_uses_purchase_tax_engine_context(self):
        self.doc.doctype = 'Subcontract Clearnce'
        self.doc.supplier = 'Supplier'
        # The factory chooses the native buying document rather than a sales proxy.
        with patch.dict(sys.modules, self.modules):
            self.service.calculate_contract_taxes(self.doc)
        self.modules['frappe'].new_doc.assert_called_once_with('Purchase Order')
        self.assertEqual(self.proxy.supplier, 'Supplier')

    def test_zero_current_quantity_is_allowed_for_draft_certificate(self):
        self.doc.doctype = 'Project Clearnce'
        self.doc.clauses[1].qty = 0
        with patch.dict(sys.modules, self.modules):
            self.service.calculate_contract_taxes(self.doc)
        self.engine.assert_not_called()
        self.assertEqual(self.doc.grand_total, 0)
        self.assertEqual(self.doc.clauses[1].amount, 0)
