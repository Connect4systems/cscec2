import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from test_tender_project_mapping import Record


class CRClausesTest(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType('frappe')
        self.frappe.whitelist = lambda: lambda fn: fn
        self.frappe.throw = MagicMock(side_effect=ValueError)
        self.frappe.get_doc = MagicMock()
        document = types.ModuleType('frappe.model.document')
        document.Document = object
        tender = types.ModuleType('contractor.clause_excel')
        tender.HEADERS = []
        tender.read_clause_excel = MagicMock(return_value=[])
        spec = importlib.util.spec_from_file_location('cr_under_test',
            Path(__file__).parents[1] / 'contractor/contractor_app/doctype/cr/cr.py')
        self.service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': self.frappe, 'frappe.model.document': document,
                tender.__name__: tender}):
            spec.loader.exec_module(self.service)

    def test_manual_rows_numbered_and_supplier_required(self):
        doc = Record(clauses=[Record(clause_title='Civil', is_group=1),
            Record(clause_title='Concrete', is_group=0, qty=2)], supplier='Supplier', numbering_mode='Automatic')
        self.service.CR.validate(doc)
        self.assertEqual([r.series_number for r in doc.clauses], ['1', '1_1'])
        doc.supplier = None
        with self.assertRaises(ValueError):
            self.service.CR.validate(doc)

    def test_submitted_requests_cannot_replace_clauses(self):
        self.frappe.get_doc.return_value = Record(docstatus=1, check_permission=MagicMock())
        with self.assertRaises(ValueError):
            self.service.editable_cr('CR-1')

    def test_project_fetch_preserves_series_and_source(self):
        doc = Record(docstatus=0, project='PROJ-1', clauses=[], name='CR-1',
            check_permission=MagicMock(), save=MagicMock())
        project = Record(project_clauses=[Record(name='row-1', is_group=1,
            series_number='4', clause_title='Civil', contractual_clause='CC-1')], check_permission=MagicMock())
        self.frappe.get_doc.side_effect = [doc, project]
        self.assertEqual(self.service.fetch_project_clauses('CR-1'), 'CR-1')
        self.assertEqual(doc.numbering_mode, 'From Excel')
        self.assertEqual(doc.clauses[0].series_number, '4')
        self.assertEqual(doc.clauses[0].project_clause, 'row-1')
        project.check_permission.assert_called_once_with('read')
        doc.save.assert_called_once()

    def test_source_reference_from_other_project_rejected(self):
        doc = Record(project='PROJ-2', supplier='Supplier', numbering_mode='Automatic',
            clauses=[Record(clause_title='Civil', is_group=1, project_clause='other-row', contractual_clause='CC-1')])
        self.frappe.get_doc.return_value = Record(project_clauses=[], check_permission=MagicMock())
        with self.assertRaises(ValueError):
            self.service.CR.validate(doc)


    def test_fetch_rejects_project_changed_since_popup(self):
        doc = Record(docstatus=0, project='PROJ-2', check_permission=MagicMock())
        self.frappe.get_doc.return_value = doc
        with self.assertRaises(ValueError):
            self.service.fetch_project_clauses('CR-1', project='PROJ-1')
        self.frappe.get_doc.assert_called_once_with('CR', 'CR-1')

    def test_partial_fetch_copies_only_selected_detail_and_heading(self):
        doc = Record(docstatus=0, project='PROJ-1', clauses=[], name='CR-1',
            check_permission=MagicMock(), save=MagicMock())
        project = Record(project_clauses=[
            Record(name='group', is_group=1, series_number='4', clause_title='Civil'),
            Record(name='a', is_group=0, series_number='4_2', parent_series='4', clause_title='A', qty=3),
            Record(name='b', is_group=0, series_number='4_7', parent_series='4', clause_title='B', qty=5)],
            check_permission=MagicMock())
        self.frappe.get_doc.side_effect = [doc, project]
        self.service.fetch_project_clauses('CR-1', fetch_all=0, selected_rows=['b'], project='PROJ-1')
        self.assertEqual([row.project_clause for row in doc.clauses], ['group', 'b'])
        self.assertEqual(doc.clauses[1].series_number, '4_7')
        self.assertEqual(doc.numbering_mode, 'From Excel')
