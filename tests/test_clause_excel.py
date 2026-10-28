import importlib.util
import io
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from openpyxl import Workbook

ROOT = Path(__file__).parents[1]


class ClauseExcelTest(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType('frappe')
        self.frappe.throw = MagicMock(side_effect=ValueError)
        self.frappe.get_doc = MagicMock()
        self.frappe.db = MagicMock()
        spec = importlib.util.spec_from_file_location('shared_excel_test', ROOT / 'contractor/clause_excel.py')
        self.excel = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': self.frappe}):
            spec.loader.exec_module(self.excel)

    def test_excel_preserves_series_and_checks_file_permission(self):
        workbook = Workbook()
        workbook.active.append(self.excel.HEADERS)
        workbook.active.append(['4', 'Civil', 1, None, None])
        workbook.active.append(['4_7', 'Concrete', 0, 12, 'm3'])
        output = io.BytesIO()
        workbook.save(output)
        file = self.frappe.get_doc.return_value
        file.get_content.return_value = output.getvalue()
        rows = self.excel.read_clause_excel('/private/files/clauses.xlsx')
        file.check_permission.assert_called_once_with('read')
        self.assertEqual(rows[1]['series_number'], '4_7')
        self.assertEqual(rows[1]['parent_series'], '4')
        self.assertEqual(rows[1]['qty'], 12)

    def test_cr_loads_with_unavailable_tender_controller(self):
        document = types.ModuleType('frappe.model.document')
        document.Document = object
        self.frappe.whitelist = lambda: lambda fn: fn
        spec = importlib.util.spec_from_file_location('cr_import_test', ROOT / 'contractor/contractor_app/doctype/cr/cr.py')
        cr = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {
                'frappe': self.frappe, 'frappe.model.document': document,
                'contractor.clause_excel': self.excel,
                'contractor.contractor_app.doctype.tender_analysis.tender_analysis': None}):
            spec.loader.exec_module(cr)
        self.assertIs(cr.read_clause_excel, self.excel.read_clause_excel)
        self.assertTrue(hasattr(cr, 'CR'))
