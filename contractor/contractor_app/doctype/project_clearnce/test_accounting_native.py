"""Run on a configured accounting TEST site; all documents roll back per test."""
import unittest
try:
    import frappe
    from frappe.tests.utils import FrappeTestCase
except ModuleNotFoundError:
    frappe = None
    FrappeTestCase = unittest.TestCase


@unittest.skipUnless(frappe, "Requires a configured Frappe/ERPNext test site")
class TestCertificateAccounting(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self.company = None
        for row in frappe.get_all("Company", fields=["name", "default_currency", "default_income_account", "default_expense_account", "cost_center", "default_receivable_account", "default_payable_account"]):
            if all(row.get(key) for key in ["default_currency", "default_income_account", "default_expense_account", "cost_center", "default_receivable_account", "default_payable_account"]):
                self.company = row
                break
        if not self.company:
            self.skipTest("A test company with default accounting accounts and Cost Center is required")
        from frappe.utils import today
        self.date = today()
        parent = frappe.db.get_value("Account", {"company": self.company.name, "root_type": "Liability", "is_group": 1}, "name")
        if not parent:
            self.skipTest("Test company needs a Liability account group")
        account = frappe.get_doc(dict(doctype="Account", account_name="_Test Certificate Retention " + frappe.generate_hash(length=6),
            company=self.company.name, parent_account=parent, is_group=0, account_currency=self.company.default_currency)).insert()
        self.retention = account.name

    def certificate(self, buying):
        from frappe.utils import today
        if buying:
            group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
            if not group:
                self.skipTest("Test site needs a Supplier Group")
            party = frappe.get_doc(dict(doctype="Supplier", supplier_name="_Test Clearnce " + frappe.generate_hash(length=6), supplier_group=group, supplier_type="Company")).insert()
        else:
            group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
            territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")
            if not group or not territory:
                self.skipTest("Test site needs Customer Group and Territory")
            party = frappe.get_doc(dict(doctype="Customer", customer_name="_Test Clearnce " + frappe.generate_hash(length=6), customer_group=group, territory=territory, customer_type="Company")).insert()
        project = frappe.new_doc("Project")
        project.project_name = "_Test Certificate " + frappe.generate_hash(length=8)
        project.company = self.company.name
        project.insert()
        doc = frappe.new_doc("Subcontract Clearnce" if buying else "Project Clearnce")
        doc.name = "_Test Certificate"
        doc.project = project.name
        doc.company = self.company.name
        doc.currency = self.company.default_currency
        doc.conversion_rate = 1
        doc.posting_date = today()
        doc.cost_center = self.company.cost_center
        doc.set("supplier" if buying else "customer", party.name)
        doc.net_total = doc.grand_total = 100
        doc.total_deductions = 10
        doc.append("deductions", dict(account=self.retention, percent=10, value=10))
        # Exercise the native accounting boundary independently of certificate source setup.
        doc.db_set = lambda field, value, **kwargs: doc.set(field, value)
        return doc

    def verify(self, buying):
        from contractor.clearance_accounting import post_accounting, cancel_accounting, WORK_ITEM
        doc = self.certificate(buying)
        post_accounting(doc)
        invoice = frappe.get_doc(doc.invoice_doctype, doc.invoice)
        self.assertEqual(invoice.docstatus, 1)
        self.assertEqual(len(invoice.items), 1)
        self.assertEqual(invoice.items[0].item_name, WORK_ITEM)
        self.assertAlmostEqual(invoice.grand_total, 100)
        self.assertAlmostEqual(invoice.outstanding_amount, 90)
        entry = frappe.get_doc("Journal Entry", doc.deduction_entry)
        self.assertEqual(entry.docstatus, 1)
        self.assertAlmostEqual(sum(row.debit-row.credit for row in entry.accounts), 0)
        cancel_accounting(doc)
        self.assertEqual(frappe.db.get_value(doc.invoice_doctype, doc.invoice, "docstatus"), 2)
        self.assertEqual(frappe.db.get_value("Journal Entry", entry.name, "docstatus"), 2)

    def test_customer_invoice_deduction_and_reversal(self):
        self.verify(False)

    def test_supplier_invoice_deduction_and_reversal(self):
        self.verify(True)
