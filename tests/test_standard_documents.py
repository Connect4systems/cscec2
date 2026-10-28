import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from test_tender_project_mapping import Record


class StandardERPNextDocumentsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[1]
        self.frappe = MagicMock()
        self.frappe.scrub.side_effect = lambda value: value.lower().replace(' ', '_')
        self.frappe.get_all.return_value = []
        self.frappe.db.exists.return_value = False
        self.frappe.db.get_value.return_value = None
        utils = types.ModuleType('frappe.utils')
        utils.now = lambda: '2026-10-28 12:00:00'
        spec = importlib.util.spec_from_file_location('standard_documents_test', self.root / 'contractor/standard_documents.py')
        self.service = importlib.util.module_from_spec(spec)
        self.patcher = patch.dict(sys.modules, {'frappe': self.frappe, 'frappe.utils': utils})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        spec.loader.exec_module(self.service)

    def test_own_field_removed_without_force_and_site_configuration_preserved(self):
        def get_value(doctype, key, *args, **kwargs):
            if doctype == 'Custom Field':
                if key == {'dt': 'Opportunity', 'fieldname': 'custom_cost_sheet'}:
                    return Record(name='Opportunity-custom_cost_sheet', module='Contractor App')
                if key == {'dt': 'Opportunity', 'fieldname': 'workflow_state'}:
                    return Record(name='Opportunity-workflow_state', module=None)
                if key == {'dt': 'Opportunity', 'fieldname': 'custom_financial_proposal'}:
                    return Record(name='Other-app-field', module='Other App')
            return None
        self.frappe.db.get_value.side_effect = get_value
        self.frappe.db.exists.side_effect = lambda dt, filters: dt == 'Workflow' and filters.get('workflow_state_field') == 'workflow_state'
        result = self.service.restore_standard_documents()
        self.frappe.delete_doc.assert_called_once_with('Custom Field', 'Opportunity-custom_cost_sheet')
        self.assertEqual(result['removed_fields'], ['Opportunity-custom_cost_sheet'])
        self.assertEqual(len(result['retained']), 2)
        self.frappe.db.sql.assert_not_called()
        self.frappe.db.sql_ddl.assert_not_called()
        self.assertEqual(self.frappe.reload_doc.call_count, 16)

    def test_empty_site_is_repeatable(self):
        first = self.service.restore_standard_documents()
        second = self.service.restore_standard_documents()
        self.assertEqual(first, second)
        self.frappe.delete_doc.assert_not_called()

    def test_native_documents_have_only_purchasing_naming_overrides(self):
        targets = {'Opportunity','Quotation','Sales Order','Sales Invoice','Purchase Order','Purchase Invoice','Purchase Receipt'}
        namespace = {}
        exec((self.root / 'contractor/hooks.py').read_text().replace('from . import __version__ as app_version', 'app_version="test"'), namespace)
        for hook in ('doctype_js', 'override_doctype_class', 'doc_events'):
            allowed = {'Purchase Order', 'Purchase Receipt'} if hook == 'override_doctype_class' else set()
            self.assertEqual(targets.intersection(namespace[hook]), allowed)
        for fixture in ('custom_field', 'doctype_link'):
            rows = json.loads((self.root / 'contractor/fixtures' / (fixture + '.json')).read_text())
            for row in rows:
                self.assertNotIn(row.get('dt') or row.get('parent'), self.service.NATIVE_DOCUMENTS)
        for doctype in targets:
            self.assertIn(doctype, self.service.NATIVE_DOCUMENTS)
        self.assertIn('Comparison', namespace['doctype_js'])
        self.assertIn('Subcontractor Custody', namespace['override_doctype_class'])

    def test_known_purchasing_and_invoice_custom_fields_are_in_restore_manifest(self):
        data = json.loads((self.root / 'contractor/patches/standard_erpnext_documents.json').read_text())
        fields = {(row['dt'],row['fieldname']) for row in data['fields']}
        for pair in [('Sales Invoice','deductions'),('Sales Invoice','clearence'),
                     ('Purchase Invoice','deductions'),('Purchase Order','custom_type'),
                     ('Opportunity','custom_cost_sheet')]:
            self.assertIn(pair, fields)


    def test_standard_cleanup_removes_former_order_type(self):
        self.frappe.db.get_value.side_effect = lambda dt, key, *args, **kwargs: (
            Record(name='Purchase Order-custom_type', module='Contractor App')
            if dt == 'Custom Field' and key == {'dt': 'Purchase Order', 'fieldname': 'custom_type'} else None)
        self.service.restore_standard_documents()
        self.frappe.delete_doc.assert_called_once_with('Custom Field', 'Purchase Order-custom_type')
