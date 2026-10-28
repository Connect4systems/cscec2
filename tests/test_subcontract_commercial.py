import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from test_subcontract_workflow import Doc


class SubcontractCommercialTest(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType('frappe')
        self.frappe.whitelist = lambda: lambda fn: fn
        self.frappe.throw = MagicMock(side_effect=ValueError)
        self.frappe.get_doc = MagicMock()
        self.frappe.get_cached_value = MagicMock(side_effect=lambda doctype, name, field: 'EGP' if doctype == 'Company' else 'Company')
        utils = types.ModuleType('frappe.utils')
        utils.flt = lambda value: float(value or 0)
        utils.today = lambda: '2026-10-28'
        self.taxes = types.ModuleType('contractor.project_contract_taxes')
        self.taxes.TOTAL_FIELDS = ('total', 'net_total', 'grand_total')
        self.taxes.calculate_contract_taxes = MagicMock(side_effect=lambda doc: doc.set('grand_total', 140))
        self.taxes.get_tax_template = MagicMock(return_value=[])
        spec = importlib.util.spec_from_file_location('commercial_test', Path(__file__).parents[1] / 'contractor/subcontract_commercial.py')
        self.service = importlib.util.module_from_spec(spec)
        self.modules = {'frappe': self.frappe, 'frappe.utils': utils, 'contractor.project_contract_taxes': self.taxes}
        self.patcher = patch.dict(sys.modules, self.modules)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        spec.loader.exec_module(self.service)

    def source(self):
        return Doc(company='Company', currency='EGP', conversion_rate=1,
            taxes_and_charges='Purchase VAT', purchasing_deductions_template='Retention',
            apply_discount_on='Net Total', additional_discount_percentage=10, discount_amount=20,
            grand_total=140, taxes=[Doc(name='source-tax', charge_type='On Net Total', rate=14, account_head='VAT'),
                Doc(name='fixed-tax', charge_type='Actual', tax_amount=50, account_head='Fees')],
            deductions=[Doc(name='source-deduction', title='Retention', account='Retention', percent=5, value=7)])

    def test_mapping_copies_edited_terms_with_new_child_identities(self):
        source = self.source()
        target = Doc(taxes=[], deductions=[])
        self.service.copy_commercial_terms(source, target)
        self.assertEqual(target.taxes_and_charges, 'Purchase VAT')
        self.assertEqual(target.purchasing_deductions_template, 'Retention')
        self.assertEqual(target.grand_total, 140)
        self.assertEqual(target.taxes[1].tax_amount, 50)
        self.assertFalse(target.taxes[0].get('name'))
        self.assertFalse(target.deductions[0].get('name'))
        self.assertEqual(target.deductions[0].title, 'Retention')
        self.assertEqual(target.deductions[0].percent, 5)

    def test_certificate_copies_percentages_and_resets_fixed_period_amounts(self):
        source = self.source()
        target = Doc(taxes=[], deductions=[])
        self.service.copy_commercial_terms(source, target, clearance=True)
        self.assertEqual(target.taxes[0].rate, 14)
        self.assertEqual(target.taxes[1].tax_amount, 0)
        self.assertEqual(target.discount_amount, 0)
        self.assertEqual(target.additional_discount_percentage, 10)
        self.assertEqual(target.deductions[0].percent, 5)
        self.assertEqual(target.deductions[0].value, 0)
        self.assertFalse(target.get('grand_total'))
        self.assertEqual(source.taxes[1].tax_amount, 50)
        self.assertEqual(source.deductions[0].value, 7)

    def test_company_currency_and_contract_amount_follow_native_totals(self):
        doc = Doc(doctype='Subcontractor Contract', clauses=[Doc(qty=1)], taxes=[], deductions=[])
        self.service.calculate_commercial(doc, Doc(company='Company'))
        self.assertEqual(doc.company, 'Company')
        self.assertEqual(doc.currency, 'EGP')
        self.assertEqual(doc.conversion_rate, 1)
        self.assertEqual(doc.contract_amount, 140)
        self.taxes.calculate_contract_taxes.assert_called_once_with(doc)

    def test_foreign_company_accounts_and_invalid_conversion_are_rejected(self):
        for doc in (Doc(doctype='CR', company='Other'),
                    Doc(doctype='CR', currency='USD', conversion_rate=0),
                    Doc(doctype='CR', taxes=[Doc(account_head='Other VAT')])):
            if doc.get('taxes'):
                self.frappe.get_cached_value.side_effect = lambda dt, name, field: 'EGP' if dt == 'Company' else 'Other'
            with self.assertRaises(ValueError):
                self.service.calculate_commercial(doc, Doc(company='Company'))
        self.taxes.calculate_contract_taxes.assert_not_called()

    def test_manual_deduction_edits_are_preserved_when_template_is_selected(self):
        source = self.source()
        source.doctype = 'CR'
        self.service.calculate_commercial(source, Doc(company='Company'))
        self.assertEqual(source.deductions[0].title, 'Retention')
        self.assertEqual(source.deductions[0].percent, 5)
        self.taxes.get_tax_template.assert_not_called()
