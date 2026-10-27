import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class Row(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    def set(self, field, value):
        self[field] = value


class ClearanceQuantityTest(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType('frappe')
        fake.whitelist = lambda: lambda fn: fn
        fake.throw = lambda text: (_ for _ in ()).throw(ValueError(text))
        utils = types.ModuleType('frappe.utils')
        utils.flt = lambda value, *args: float(value or 0)
        utils.today = lambda: '2026-10-27'
        progress = types.ModuleType('contractor.project_progress')
        progress.CERTIFICATES = ('Project Clearnce', 'Subcontract Clearnce')
        progress.executed_quantities = MagicMock(side_effect=lambda *args, **kwargs: {'clause': 20} if kwargs.get('supplier') else {'clause': 60})
        progress.refresh_project = MagicMock()
        spec = importlib.util.spec_from_file_location('clearances_under_test', Path(__file__).parents[1]/'contractor/project_clearances.py')
        self.service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': fake, 'frappe.utils': utils, 'contractor.project_progress': progress}):
            spec.loader.exec_module(self.service)
        self.project = Row(name='PROJ-1', project_clauses=[Row(name='clause', is_group=0, qty=100, uom='m', series_number='1_1', contractual_clause='CC-1')])
        self.row = Row(project_clause_ref='clause', qty=10, idx=1)
        self.doc = Row(name='CERT-1', doctype='Subcontract Clearnce', supplier='Supplier', clauses=[self.row])

    def test_supplier_previous_is_scoped_but_remaining_uses_all_suppliers(self):
        self.assertTrue(self.service.set_quantities(self.doc, self.project))
        self.assertEqual(self.row.previous_qty, 20)
        self.assertEqual(self.row.project_previous_qty, 60)
        self.assertEqual(self.row.remaining_qty, 30)
        self.assertEqual(self.row.total_executed_qty, 30)

    def test_duplicate_rows_and_cross_project_references_rejected(self):
        self.doc.clauses.append(Row(project_clause_ref='clause', qty=5))
        with self.assertRaisesRegex(ValueError, 'unique clause'):
            self.service.set_quantities(self.doc, self.project)
        self.doc.clauses = [Row(project_clause_ref='another-project-clause', qty=1)]
        with self.assertRaisesRegex(ValueError, 'belonging to this Project'):
            self.service.set_quantities(self.doc, self.project)

    def test_total_quantity_limit_checks_previous_plus_current(self):
        self.row.qty = 41
        with self.assertRaisesRegex(ValueError, 'remaining'):
            self.service.set_quantities(self.doc, self.project)
