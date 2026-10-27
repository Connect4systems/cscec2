"""Native dashboard routes; run against a migrated Frappe test site."""
import unittest

try:
    import frappe
    from frappe.tests.utils import FrappeTestCase
except ModuleNotFoundError:
    frappe = None
    FrappeTestCase = unittest.TestCase


@unittest.skipUnless(frappe, "Requires a Frappe test site")
class TestConnections(FrappeTestCase):
    def test_offer_and_contract_internal_connections_deduplicate_notes(self):
        from frappe.desk.notifications import get_internal_links
        from contractor.connections import dashboard_data
        for doctype in ('Project Offer', 'Project Contract'):
            doc = frappe.new_doc(doctype)
            doc.tender_analysis = 'TA-test'
            for note in ('CN-1', 'CN-1', 'CN-2'):
                doc.append('clauses', {'costing_note': note})
            data = dashboard_data(doctype)
            source = get_internal_links(doc, data['internal_links']['Tender Analysis'], 'Tender Analysis')
            notes = get_internal_links(doc, data['internal_links']['Costing Note'], 'Costing Note')
            self.assertEqual(source['names'], ['TA-test'])
            self.assertEqual(notes['count'], 2)
            self.assertEqual(notes['names'], ['CN-1', 'CN-2'])
