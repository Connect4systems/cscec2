import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class Doc:
    def __init__(self, **values):
        self.__dict__.update(values)
    def get(self, field, default=None):
        return getattr(self, field, default)
    def set(self, field, value):
        setattr(self, field, value)
    def update(self, values):
        self.__dict__.update(values)
    def append(self, field, values):
        getattr(self, field).append(Doc(**values))
    def as_dict(self):
        return dict(self.__dict__)
    def precision(self, field):
        return 2
    def db_set(self, field, value, **kwargs):
        setattr(self, field, value)


class ClearanceAccountingTest(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType('frappe')
        fake.throw = lambda text: (_ for _ in ()).throw(ValueError(text))
        fake.db = MagicMock()
        fake.db.exists.return_value = True
        def cached(doctype, name, field):
            if doctype == 'Account':
                return 'EGP' if field == 'account_currency' else 'Tax'
            return {'default_income_account': 'Income', 'default_expense_account': 'Expense',
                'cost_center': 'Main', 'default_currency': 'EGP', 'round_off_account': 'Rounding'}.get(field)
        fake.get_cached_value = MagicMock(side_effect=cached)
        utils = types.ModuleType('frappe.utils')
        utils.flt = lambda value, precision=None: round(float(value or 0), precision) if precision is not None else float(value or 0)
        party = types.ModuleType('erpnext.accounts.party')
        party.get_party_account = lambda kind, *args: 'Payable' if kind == 'Supplier' else 'Receivable'
        taxes = types.ModuleType('contractor.project_contract_taxes')
        taxes.tax_values = lambda row: row.as_dict()
        self.invoice = Doc(items=[], taxes=[], docstatus=0)
        self.entry = Doc(accounts=[], docstatus=0)
        self.log = []
        def insert_invoice():
            self.invoice.name = 'INV-1'
            self.invoice.grand_total = self.invoice.items[0].rate + sum(row.tax_amount for row in self.invoice.taxes)
            return self.invoice
        self.invoice.insert = MagicMock(side_effect=insert_invoice)
        self.invoice.submit = MagicMock(side_effect=lambda: setattr(self.invoice, 'docstatus', 1))
        self.invoice.cancel = MagicMock(side_effect=lambda: self.log.append('invoice'))
        self.entry.insert = MagicMock(side_effect=lambda: setattr(self.entry, 'name', 'JE-1'))
        self.entry.submit = MagicMock(side_effect=lambda: setattr(self.entry, 'docstatus', 1))
        self.entry.cancel = MagicMock(side_effect=lambda: self.log.append('journal'))
        fake.new_doc = MagicMock(side_effect=lambda doctype: self.entry if doctype == 'Journal Entry' else self.invoice)
        item = Doc(name='WORK-1', item_name='بنود اعمال', stock_uom='Nos', is_stock_item=0, disabled=0, is_sales_item=1, is_purchase_item=1)
        fake.get_doc = MagicMock(side_effect=lambda doctype, name: item if doctype == 'Item' else self.entry if doctype == 'Journal Entry' else self.invoice)
        self.fake = fake
        self.modules = {'frappe': fake, 'frappe.utils': utils, 'erpnext.accounts.party': party,
            'contractor.project_contract_taxes': taxes}
        spec = importlib.util.spec_from_file_location('accounting_under_test', Path(__file__).parents[1]/'contractor/clearance_accounting.py')
        self.service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, self.modules):
            spec.loader.exec_module(self.service)
        self.doc = Doc(doctype='Project Clearnce', name='CERT-1', company='Company', project='PROJ-1',
            customer='Customer', supplier='Supplier', currency='EGP', conversion_rate=1,
            posting_date='2026-10-27', net_total=100, grand_total=114, total_deductions=5.7,
            taxes=[Doc(charge_type='On Item Quantity', tax_amount=14, tax_amount_after_discount_amount=14,
                account_head='VAT', included_in_print_rate=0, row_id=None)],
            deductions=[Doc(account='Retention', value=5.7)])

    def post(self):
        with patch.dict(sys.modules, self.modules):
            self.service.post_accounting(self.doc)

    def test_sales_invoice_has_one_work_item_and_deductions_only_journal(self):
        self.post()
        self.assertEqual(len(self.invoice.items), 1)
        self.assertEqual(self.invoice.items[0].item_name, 'بنود اعمال')
        self.assertEqual(self.invoice.items[0].qty, 1)
        self.assertEqual(self.invoice.items[0].rate, 100)
        self.assertEqual(self.invoice.taxes[0].charge_type, 'Actual')
        self.assertEqual(self.invoice.grand_total, 114)
        self.assertEqual(self.entry.accounts[0].debit, 5.7)
        self.assertEqual(self.entry.accounts[-1].credit, 5.7)
        self.assertEqual(self.entry.accounts[-1].reference_name, 'INV-1')
        self.assertEqual(self.doc.invoice_doctype, 'Sales Invoice')
        self.assertEqual([call.args[0] for call in self.fake.new_doc.call_args_list], ['Sales Invoice', 'Journal Entry'])

    def test_purchase_invoice_uses_supplier_and_opposite_deduction_direction(self):
        self.doc.doctype = 'Subcontract Clearnce'
        self.post()
        self.assertEqual(self.doc.invoice_doctype, 'Purchase Invoice')
        self.assertEqual(self.invoice.supplier, 'Supplier')
        self.assertEqual(self.invoice.items[0].expense_account, 'Expense')
        self.assertEqual(self.entry.accounts[0].credit, 5.7)
        self.assertEqual(self.entry.accounts[-1].debit, 5.7)
        self.assertEqual(self.entry.accounts[-1].party_type, 'Supplier')

    def test_repeated_posting_does_not_duplicate_invoice_or_journal(self):
        self.post()
        self.post()
        self.invoice.insert.assert_called_once()
        self.entry.insert.assert_called_once()

    def test_no_deductions_means_no_extra_journal(self):
        self.doc.total_deductions = 0
        self.doc.deductions = []
        self.post()
        self.entry.insert.assert_not_called()

    def test_cancellation_reverses_journal_before_invoice(self):
        self.post()
        self.service.cancel_accounting(self.doc)
        self.assertEqual(self.log, ['journal', 'invoice'])

    def test_company_currency_rounding_remains_balanced(self):
        self.doc.invoice_doctype = 'Sales Invoice'
        self.doc.invoice = 'INV-1'
        self.doc.currency = 'USD'
        self.doc.conversion_rate = 1.2
        self.doc.total_deductions = 0.06
        self.doc.deductions = [Doc(account='Retention', value=0.03), Doc(account='Retention', value=0.03)]
        self.fake.get_cached_value.side_effect = lambda dt, name, field: ('Rounding' if dt=='Company' else 'EGP' if name=='Rounding' else 'USD') if field != 'account_type' else 'Tax'
        rows = self.service.deduction_lines(self.doc, 'Receivable', 'EGP', 'Main')
        self.assertAlmostEqual(sum(row.get('debit', 0)-row.get('credit', 0) for row in rows), 0)
