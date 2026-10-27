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

    def set(self, field, values):
        setattr(self, field, [Record(**row) for row in values] if field == 'deductions' else values)

    def as_dict(self):
        return dict(self.__dict__)

    def check_permission(self, permission):
        pass

    def get_doc_before_save(self):
        return None


class TenderDeductionsTest(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType('frappe')
        fake.whitelist = lambda: lambda fn: fn
        fake.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
        fake.get_cached_value = MagicMock(return_value='Company')
        self.template = Record(deductions=[Record(name='template-row', title='Retention', account='Account', percent=5)])
        fake.get_doc = MagicMock(return_value=self.template)
        self.fake = fake
        spec = importlib.util.spec_from_file_location('deductions_under_test',
            Path(__file__).parents[1] / 'contractor/deductions.py')
        self.service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': fake}):
            spec.loader.exec_module(self.service)

    def test_template_selection_copies_rows_and_calculates_values(self):
        doc = Record(company='Company', selling_deductions_template='Retention template', deductions=[], total_amount=200)
        self.service.update_tender_deductions(doc)
        self.assertEqual(doc.deductions[0].title, 'Retention')
        self.assertFalse(hasattr(doc.deductions[0], 'name'))
        self.assertEqual(doc.total_deductions, 10)
        self.assertEqual(doc.net_payable, 190)

    def test_manual_rows_are_preserved_when_template_is_selected(self):
        doc = Record(company='Company', selling_deductions_template='Retention template',
            deductions=[Record(title='Negotiated', account='Account', percent=7)], total_amount=200)
        self.service.update_tender_deductions(doc)
        self.assertEqual(doc.deductions[0].title, 'Negotiated')
        self.assertEqual(doc.total_deductions, 14)
        doc.total_amount = 300
        self.service.update_tender_deductions(doc)
        self.assertEqual(doc.total_deductions, 21)

    def test_account_company_and_excessive_deductions_are_rejected(self):
        self.fake.get_cached_value.return_value = 'Other Company'
        with self.assertRaisesRegex(ValueError, 'document company'):
            self.service.get_selling_deductions('Template', 'Company')
        self.fake.get_cached_value.return_value = 'Company'
        doc = Record(company='Company', total_amount=100, deductions=[Record(account='Account', percent=101)])
        with self.assertRaisesRegex(ValueError, 'between zero and 100'):
            self.service.update_tender_deductions(doc)
