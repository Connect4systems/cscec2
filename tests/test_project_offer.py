import importlib.util
import json
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

    def append(self, field, values):
        getattr(self, field).append(Record(**values))

    def as_dict(self):
        return dict(self.__dict__)

    def check_permission(self, permission):
        pass


class ProjectOfferConversionTest(unittest.TestCase):
    def setUp(self):
        self.fake = types.ModuleType('frappe')
        self.fake.whitelist = lambda: lambda fn: fn
        self.fake.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
        self.fake.db = MagicMock()
        self.fake.db.get_value.return_value = None
        services = types.ModuleType('contractor.project_contract')
        services.require_ready = MagicMock()
        services.commercial_creation_status = MagicMock()
        services.create_commercial_document = MagicMock()
        self.services = services
        self.offer = Record(name='POF-1', doctype='Project Offer', docstatus=1,
            title='Negotiated offer', tender_analysis='TA-1', company='Company', currency='EGP',
            customer='Customer', status='Submitted', transaction_date='2026-10-27', delivery_date='2026-11-01',
            conversion_rate=1, terms='Offer terms', discount_amount=10,
            clauses=[Record(name='offer-row', parent='POF-1', doctype='Project Offer Clause', docstatus=1,
                source_row='tender-row', contractual_clause='CC-1', qty=3, rate=77, costing_note='CN-1')],
            taxes=[Record(name='offer-tax', parent='POF-1', docstatus=1,
                charge_type='On Previous Row Total', row_id='1', rate=5)],
            deductions=[Record(name='offer-deduction', parent='POF-1', title='Retention', percent=5)])
        self.tender = Record(name='TA-1')
        schema = json.loads((Path(__file__).parents[1] / 'contractor/contractor_app/doctype/project_contract/project_contract.json').read_text())
        self.contract = Record(doctype='Project Contract', docstatus=0,
            meta=Record(fields=[Record(**field) for field in schema['fields']]))
        self.fake.new_doc = MagicMock(return_value=self.contract)
        self.fake.get_doc = MagicMock(side_effect=lambda doctype, name:
            {'Project Offer': self.offer, 'Tender Analysis': self.tender, 'Project Contract': self.contract}[doctype])
        self.modules = {'frappe': self.fake, 'contractor.project_contract': services}
        spec = importlib.util.spec_from_file_location('project_offer_under_test',
            Path(__file__).parents[1] / 'contractor/project_offer.py')
        self.service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, self.modules):
            spec.loader.exec_module(self.service)

    def test_only_submitted_offer_can_be_converted(self):
        for status in (0, 2):
            self.offer.docstatus = status
            with self.assertRaisesRegex(ValueError, 'Submit the Project Offer'):
                self.service.create_project_contract('POF-1')
        self.fake.new_doc.assert_not_called()

    def test_conversion_preserves_negotiated_values_and_copies_new_child_rows(self):
        doc = self.service.create_project_contract('POF-1')['doc']
        self.assertEqual(doc.project_offer, 'POF-1')
        self.assertEqual(doc.docstatus, 0)
        self.assertEqual(doc.status, 'Draft')
        self.assertEqual(doc.clauses[0].qty, 3)
        self.assertEqual(doc.clauses[0].rate, 77)
        self.assertEqual(doc.clauses[0].source_row, 'tender-row')
        self.assertFalse(hasattr(doc.clauses[0], 'name'))
        self.assertFalse(hasattr(doc.clauses[0], 'parent'))
        self.assertEqual(doc.taxes[0].charge_type, 'On Previous Row Total')
        self.assertEqual(doc.taxes[0].row_id, '1')
        self.assertEqual(doc.deductions[0].title, 'Retention')
        self.assertEqual(doc.terms, 'Offer terms')
        self.services.require_ready.assert_called_once_with(self.tender)

    def test_repeated_conversion_opens_existing_contract(self):
        self.fake.db.get_value.return_value = Record(name='PC-1', project_offer='POF-1')
        self.assertEqual(self.service.create_project_contract('POF-1'), {'existing': 'PC-1'})
        self.fake.new_doc.assert_not_called()

    def test_existing_contract_from_another_source_blocks_conversion(self):
        self.fake.db.get_value.return_value = Record(name='PC-1', project_offer='POF-OTHER')
        with self.assertRaisesRegex(ValueError, 'already has an active Project Contract'):
            self.service.create_project_contract('POF-1')
        self.fake.new_doc.assert_not_called()

    def test_linked_contract_must_match_submitted_offer_header(self):
        self.contract.project_offer = 'POF-1'
        self.contract.tender_analysis = 'TA-1'
        self.contract.company = 'OTHER'
        self.contract.currency = 'EGP'
        self.contract.customer = 'Customer'
        with self.assertRaisesRegex(ValueError, 'must match its submitted Project Offer'):
            self.service.validate_offer_source(self.contract)
