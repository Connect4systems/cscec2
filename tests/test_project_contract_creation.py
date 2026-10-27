import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class Doc(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__

    def append(self, field, values):
        self.setdefault(field, []).append(Doc(values))

    def check_permission(self, permission):
        pass


class ProjectContractCreationTest(unittest.TestCase):
    def setUp(self):
        self.fake = types.ModuleType('frappe')
        self.fake.whitelist = lambda: lambda fn: fn
        self.fake.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
        self.fake.get_all = MagicMock(return_value=[Doc(name='CN-1', docstatus=1)])
        self.fake.db = MagicMock()
        self.fake.db.get_value.return_value = None
        self.fake.get_cached_value = MagicMock(return_value='EGP')
        self.fake.new_doc = MagicMock(side_effect=lambda name: Doc(doctype=name))
        self.tender = Doc(name='TA-1', title='Contract', company='Company', currency='EGP',
            tender_number='123', party_type='Customer', party_name='Customer', clauses=[
                Doc(name='source-1', is_group=1, series_number='1', clause_title='Civil', contractual_clause='CC-1'),
                Doc(name='source-2', is_group=0, series_number='1_1', clause_title='Concrete', contractual_clause='CC-2',
                    qty=2, rate=50, amount=100, uom='Nos', applied_costing_note='CN-1')])
        self.fake.get_doc = MagicMock(return_value=self.tender)
        utils = types.ModuleType('frappe.utils')
        utils.today = lambda: '2026-10-27'
        pricing = types.ModuleType('contractor.tender_pricing')
        pricing.submitted_boq_links = MagicMock(return_value={'source-2': 'BOQ-1'})
        self.modules = {'frappe': self.fake, 'frappe.utils': utils, 'contractor.tender_pricing': pricing}
        spec = importlib.util.spec_from_file_location('project_contract_under_test',
            Path(__file__).parents[1] / 'contractor/project_contract.py')
        self.service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, self.modules):
            spec.loader.exec_module(self.service)

    def test_direct_creation_rejects_a_draft_costing_note(self):
        self.fake.get_all.return_value.append(Doc(name='CN-DRAFT', docstatus=0))
        with self.assertRaisesRegex(ValueError, 'Submit all'):
            self.service.create_project_contract('TA-1')
        self.fake.new_doc.assert_not_called()

    def test_creation_copies_clause_prices_and_stable_references(self):
        with patch.dict(sys.modules, self.modules):
            doc = self.service.create_project_contract('TA-1')['doc']
        self.assertEqual(doc.contractor_order, 1)
        self.assertEqual(doc.customer, 'Customer')
        self.assertEqual(doc.conversion_rate, 1)
        self.assertEqual(doc.clauses[1].source_row, 'source-2')
        self.assertEqual(doc.clauses[1].rate, 50)
        self.assertEqual(doc.clauses[1].costing_note, 'CN-1')
        self.assertEqual(doc.clauses[1].submitted_boq, 'BOQ-1')

    def test_lead_requires_selecting_a_customer_and_foreign_conversion(self):
        self.tender.party_type = 'Lead'
        self.tender.currency = 'USD'
        with patch.dict(sys.modules, self.modules):
            doc = self.service.create_project_contract('TA-1')['doc']
        self.assertIsNone(doc.customer)
        self.assertEqual(doc.conversion_rate, 0)

    def test_tender_offer_uses_same_mapping_as_contract(self):
        with patch.dict(sys.modules, self.modules):
            doc = self.service.create_commercial_document('TA-1', 'Project Offer')['doc']
        self.assertEqual(doc.doctype, 'Project Offer')
        self.assertEqual(doc.clauses[1].source_row, 'source-2')
        self.assertEqual(doc.clauses[1].rate, 50)
        self.assertEqual(doc.clauses[1].costing_note, 'CN-1')

    def test_draft_costing_blocks_offer_creation_too(self):
        self.fake.get_all.return_value = [Doc(name='CN-1', docstatus=0)]
        with self.assertRaisesRegex(ValueError, 'Submit all'):
            self.service.create_commercial_document('TA-1', 'Project Offer')
        self.fake.new_doc.assert_not_called()
