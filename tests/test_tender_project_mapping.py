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

    def append(self, field, row):
        getattr(self, field).append(Record(**row))

    def check_permission(self, permission):
        pass


class TenderProjectMappingTest(unittest.TestCase):
    def test_project_text_copies_to_costing_note(self):
        fake = types.ModuleType('frappe')
        fake.whitelist = lambda: lambda fn: fn
        tender = Record(name='TA-1', project='Hospital project', tender_number='123',
            party_type='Customer', party_name='Customer', currency='EGP', numbering_mode='Automatic',
            clauses=[Record(name='source', contractual_clause='CC-1', clause_title='Civil',
                is_group=1, series_number='1', parent_series='', qty=0, uom=None)])
        note = Record(costing_note_items=[])
        fake.get_doc = MagicMock(return_value=tender)
        fake.new_doc = MagicMock(return_value=note)
        utils = types.ModuleType('frappe.utils')
        utils.flt = lambda value: float(value or 0)
        document = types.ModuleType('frappe.model.document')
        document.Document = object
        spec = importlib.util.spec_from_file_location('tender_mapping_under_test',
            Path(__file__).parents[1] / 'contractor/contractor_app/doctype/tender_analysis/tender_analysis.py')
        service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': fake, 'frappe.utils': utils, 'frappe.model.document': document}):
            spec.loader.exec_module(service)
            result = service.create_costing_note('TA-1')
        self.assertEqual(result.project, 'Hospital project')
        self.assertEqual(result.tender_analysis, 'TA-1')
