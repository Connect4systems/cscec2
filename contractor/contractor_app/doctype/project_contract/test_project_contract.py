"""Native ERPNext calculation checks; run on a Frappe site after migration."""
import unittest

try:
    import frappe
    from frappe.tests.utils import FrappeTestCase
except ModuleNotFoundError:
    frappe = None
    FrappeTestCase = unittest.TestCase


@unittest.skipUnless(frappe, "Requires a Frappe/ERPNext test site")
class TestProjectContract(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self.company = frappe.db.get_value("Company", {}, "name")
        if not self.company:
            self.skipTest("Create a test company first")
        self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
        self.account = frappe.db.get_value("Account", {"company": self.company, "is_group": 0}, "name")
        if not self.account:
            self.skipTest("Test company needs an account")

    def contract(self, qty=2, rate=100):
        doc = frappe.new_doc("Project Contract")
        doc.company = self.company
        doc.currency = self.currency
        doc.conversion_rate = 1
        doc.disable_rounded_total = 1
        doc.append("clauses", dict(is_group=1, clause_title="Group", qty=999, rate=999))
        doc.append("clauses", dict(is_group=0, clause_title="Detail", source_row="test-clause",
            qty=qty, rate=rate))
        return doc

    def tax(self, doc, charge_type="On Net Total", **values):
        return doc.append("taxes", dict(charge_type=charge_type, account_head=self.account,
            description="Test tax", **values))

    def test_native_previous_row_and_quantity_taxes(self):
        from contractor.project_contract_taxes import calculate_contract_taxes
        doc = self.contract()
        self.tax(doc, rate=10)
        self.tax(doc, charge_type="On Previous Row Amount", row_id="1", rate=20)
        self.tax(doc, charge_type="On Item Quantity", rate=3)
        doc.append("deductions", dict(title="Retention", percent=5))
        calculate_contract_taxes(doc)
        self.assertAlmostEqual(doc.total, 200)
        self.assertAlmostEqual(doc.total_taxes_and_charges, 30)
        self.assertAlmostEqual(doc.grand_total, 230)
        self.assertAlmostEqual(doc.net_payable, 218.5)

    def test_native_included_tax(self):
        from contractor.project_contract_taxes import calculate_contract_taxes
        doc = self.contract(qty=1, rate=110)
        self.tax(doc, rate=10, included_in_print_rate=1)
        calculate_contract_taxes(doc)
        self.assertAlmostEqual(doc.net_total, 100)
        self.assertAlmostEqual(doc.total_taxes_and_charges, 10)
        self.assertAlmostEqual(doc.grand_total, 110)

    def test_native_discount(self):
        from contractor.project_contract_taxes import calculate_contract_taxes
        doc = self.contract()
        doc.apply_discount_on = "Net Total"
        doc.discount_amount = 20
        self.tax(doc, rate=10)
        calculate_contract_taxes(doc)
        self.assertAlmostEqual(doc.net_total, 180)
        self.assertAlmostEqual(doc.total_taxes_and_charges, 18)
        self.assertAlmostEqual(doc.grand_total, 198)
