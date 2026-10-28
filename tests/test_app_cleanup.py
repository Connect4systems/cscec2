import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class AppCleanupTest(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType('frappe')
        self.frappe.db = MagicMock()
        self.frappe.db.get_value.return_value = {'module': 'Contractor App', 'custom': 0}
        self.frappe.db.table_exists.return_value = True
        self.frappe.db.count.return_value = 0
        self.frappe.get_all = MagicMock(return_value=[])
        self.frappe.get_doc = MagicMock()
        self.frappe.delete_doc = MagicMock()
        self.frappe.LinkExistsError = type('LinkExistsError', (Exception,), {})
        self.links = types.ModuleType('frappe.model.delete_doc')
        self.links.check_if_doc_is_linked = MagicMock()
        self.links.check_if_doc_is_dynamically_linked = MagicMock()
        self.modules = {'frappe': self.frappe, 'frappe.model.delete_doc': self.links}
        path = Path(__file__).parents[1]/'contractor/app_cleanup.py'
        spec = importlib.util.spec_from_file_location('cleanup_under_test', path)
        self.service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, self.modules):
            spec.loader.exec_module(self.service)

    def cleanup(self):
        with patch.dict(sys.modules, self.modules):
            return self.service.retire_unused_doctypes()

    def test_only_empty_unused_definitions_removed_without_force(self):
        results = self.cleanup()
        self.assertTrue(all(row['removed'] for row in results))
        self.assertEqual([call.args for call in self.frappe.delete_doc.call_args_list],
            [('DocType', 'E-Language'), ('DocType', 'Edu')])
        self.assertTrue(all(not call.kwargs for call in self.frappe.delete_doc.call_args_list))
        self.frappe.db.sql.assert_not_called()

    def test_existing_records_preserve_metadata(self):
        self.frappe.db.count.return_value = 1
        results = self.cleanup()
        self.frappe.delete_doc.assert_not_called()
        self.assertTrue(all('Contains existing records' in row['reasons'] for row in results))

    def test_custom_or_other_app_definitions_are_not_removed(self):
        for info in ({'module': 'HR', 'custom': 0}, {'module': 'Contractor App', 'custom': 1}):
            self.frappe.db.get_value.return_value = info
            self.cleanup()
        self.frappe.delete_doc.assert_not_called()

    def test_external_table_definition_blocks_retirement_even_without_rows(self):
        self.frappe.get_all.side_effect = lambda source, **kwargs: (
            [{'dt': 'Employee', 'fieldname': 'education'}] if source == 'Custom Field' else [])
        results = self.cleanup()
        self.frappe.delete_doc.assert_not_called()
        self.assertTrue(all('Custom Field: Employee.education' in row['reasons'] for row in results))

    def test_dynamic_configuration_link_blocks_retirement(self):
        self.links.check_if_doc_is_dynamically_linked.side_effect = self.frappe.LinkExistsError('Used by configuration')
        results = self.cleanup()
        self.frappe.delete_doc.assert_not_called()
        self.assertTrue(all('Used by configuration' in row['reasons'] for row in results))

    def test_missing_definition_and_missing_table_are_safe_to_retry(self):
        self.frappe.db.get_value.return_value = None
        self.assertTrue(all(not row['exists'] for row in self.cleanup()))
        self.frappe.db.get_value.return_value = {'module': 'Contractor App', 'custom': 0}
        self.frappe.db.table_exists.return_value = False
        self.cleanup()
        self.frappe.delete_doc.assert_not_called()

    def test_active_dependencies_still_have_schemas_but_retired_ones_do_not(self):
        root = Path(__file__).parents[1]/'contractor/contractor_app/doctype'
        schemas = {json.loads(path.read_text(encoding='utf-8'))['name'] for path in root.glob('*/*.json')}
        self.assertTrue(set(self.service.RETAINED_DEPENDENCIES).issubset(schemas))
        self.assertFalse(set(self.service.RETIRED_DOCTYPES).intersection(schemas))
