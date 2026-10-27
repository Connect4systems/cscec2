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

    def update(self, values):
        self.__dict__.update(values)

    def as_dict(self):
        return dict(self.__dict__)

    def append(self, field, values):
        getattr(self, field).append(Record(**values))

    def check_permission(self, permission):
        pass


class ContractProjectCreationTest(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType('frappe')
        fake.whitelist = lambda: lambda fn: fn
        fake.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
        fake.db = MagicMock()
        fake.db.get_value.return_value = None
        fake.db.exists.return_value = False
        self.contract = Record(name='PC-1', docstatus=1, project='New hospital',
            company='Company', customer='Customer', transaction_date='2026-10-27', delivery_date='2026-11-01',
            tender_analysis='TA-1', project_offer='POF-1', currency='EGP', grand_total=110,
            clauses=[Record(name='pc-row-1', parent='PC-1', is_group=1, series_number='1', clause_title='Civil'),
                Record(name='pc-row-2', parent='PC-1', is_group=0, series_number='1_1', qty=2, rate=50,
                    amount=100, net_amount=100, clause_title='Concrete', source_row='tender-row',
                    contractual_clause='CC-1', costing_note='CN-1', submitted_boq='BOQ-1')])
        self.project = Record(project_clauses=[])
        def insert():
            self.project.name = 'PROJ-0001'
            return self.project
        self.project.insert = MagicMock(side_effect=insert)
        fake.get_doc = MagicMock(side_effect=lambda doctype, name:
            self.contract if doctype == 'Project Contract' else self.project)
        fake.new_doc = MagicMock(return_value=self.project)
        def set_value(doctype, name, field, value=None, **kwargs):
            if doctype == 'Project Contract':
                if isinstance(field, dict):
                    self.contract.update(field)
                else:
                    setattr(self.contract, field, value)
        fake.db.set_value.side_effect = set_value
        self.fake = fake
        spec = importlib.util.spec_from_file_location('contract_projects_under_test',
            Path(__file__).parents[1] / 'contractor/contract_projects.py')
        self.service = importlib.util.module_from_spec(spec)
        names = types.ModuleType('contractor.project_names')
        names.fill_project_name = MagicMock()
        with patch.dict(sys.modules, {'frappe': fake, 'contractor.project_names': names}):
            spec.loader.exec_module(self.service)

    def test_submission_project_name_and_full_clause_snapshot(self):
        self.assertEqual(self.service.create_project('PC-1'), {'project': 'PROJ-0001'})
        self.assertEqual(self.project.project_name, 'New hospital')
        self.assertEqual(self.project.project_contract, 'PC-1')
        self.assertEqual(self.contract.created_project, 'PROJ-0001')
        self.assertEqual(self.project.project_offer, 'POF-1')
        self.assertEqual(len(self.project.project_clauses), 2)
        row = self.project.project_clauses[1]
        self.assertEqual(row.series_number, '1_1')
        self.assertEqual(row.source_row, 'tender-row')
        self.assertEqual(row.rate, 50)
        self.assertEqual(row.submitted_boq, 'BOQ-1')
        self.assertFalse(hasattr(row, 'name'))
        self.assertFalse(hasattr(row, 'parent'))

    def test_repeat_request_reuses_same_project(self):
        first = self.service.create_project('PC-1')
        self.assertEqual(self.service.create_project('PC-1'), first)
        self.project.insert.assert_called_once()

    def test_draft_and_cancelled_contracts_cannot_create_project(self):
        for status in (0, 2):
            self.contract.docstatus = status
            with self.assertRaisesRegex(ValueError, 'Submit the Project Contract'):
                self.service.create_project('PC-1')
        self.fake.new_doc.assert_not_called()

    def test_empty_and_existing_project_names_are_rejected(self):
        self.contract.project = ' '
        with self.assertRaisesRegex(ValueError, 'Enter the Project name'):
            self.service.create_project('PC-1')
        self.contract.project = 'Existing project'
        self.fake.db.exists.return_value = True
        with self.assertRaisesRegex(ValueError, 'already used by another Project'):
            self.service.create_project('PC-1')
        self.project.insert.assert_not_called()
