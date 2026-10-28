"""Native buying-tax checks; run on a migrated Frappe/ERPNext test site."""
import unittest

try:
    import frappe
    from frappe.tests.utils import FrappeTestCase
except ModuleNotFoundError:
    frappe = None
    FrappeTestCase = unittest.TestCase


@unittest.skipUnless(frappe, 'Requires a Frappe/ERPNext test site')
class TestSubcontractorContract(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self.company = frappe.db.get_value('Company', {}, 'name')
        if not self.company:
            self.skipTest('Create a test Company first')
        self.currency = frappe.get_cached_value('Company', self.company, 'default_currency')
        self.account = frappe.db.get_value('Account', {'company': self.company, 'is_group': 0}, 'name')
        if not self.account:
            self.skipTest('Create a leaf Account for the test Company')

    def commercial(self, doctype='Subcontractor Contract', qty=2, rate=100):
        doc = frappe.new_doc(doctype)
        doc.company = self.company
        doc.currency = self.currency
        doc.conversion_rate = 1
        doc.disable_rounded_total = 1
        doc.append('clauses', dict(is_group=1, clause_title='Group'))
        doc.append('clauses', dict(clause_title='Manual detail', qty=qty, rate=rate))
        doc.append('taxes', dict(charge_type='On Net Total', account_head=self.account,
            description='Test VAT', category='Total', add_deduct_tax='Add', rate=10))
        doc.append('deductions', dict(title='Retention', account=self.account, percent=5))
        return doc

    def test_native_cr_and_subcontract_taxes_and_deductions(self):
        from contractor.project_contract_taxes import calculate_contract_taxes
        for doctype in ('CR', 'Subcontractor Contract'):
            doc = self.commercial(doctype)
            calculate_contract_taxes(doc)
            self.assertAlmostEqual(doc.total, 200)
            self.assertAlmostEqual(doc.grand_total, 220)
            self.assertAlmostEqual(doc.total_deductions, 11)
            self.assertAlmostEqual(doc.net_payable, 209)
            self.assertAlmostEqual(doc.clauses[0].amount, 200)

    def test_clearance_deductions_use_period_total(self):
        from contractor.project_contract_taxes import calculate_contract_taxes
        from contractor.subcontract_commercial import copy_commercial_terms
        source = self.commercial()
        calculate_contract_taxes(source)
        certificate = frappe.new_doc('Subcontract Clearnce')
        copy_commercial_terms(source, certificate, clearance=True)
        certificate.append('clauses', dict(clause_title='This period', qty=1, rate=100))
        calculate_contract_taxes(certificate)
        self.assertAlmostEqual(certificate.grand_total, 110)
        self.assertAlmostEqual(certificate.total_deductions, 5.5)
        self.assertAlmostEqual(certificate.net_payable, 104.5)
        self.assertAlmostEqual(source.total_deductions, 11)

    def test_native_purchase_included_tax_and_discount(self):
        from contractor.project_contract_taxes import calculate_contract_taxes
        included = self.commercial(qty=1, rate=110)
        included.taxes[0].included_in_print_rate = 1
        calculate_contract_taxes(included)
        self.assertAlmostEqual(included.net_total, 100)
        self.assertAlmostEqual(included.grand_total, 110)
        discounted = self.commercial()
        discounted.apply_discount_on = 'Net Total'
        discounted.discount_amount = 20
        calculate_contract_taxes(discounted)
        self.assertAlmostEqual(discounted.net_total, 180)
        self.assertAlmostEqual(discounted.grand_total, 198)
