import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class ProjectAbbreviationTest(unittest.TestCase):
    def test_repairs_visibility_order_and_metadata(self):
        frappe = MagicMock()
        field_module = types.ModuleType('frappe.custom.doctype.custom_field.custom_field')
        field_module.create_custom_fields = MagicMock()
        utils = types.ModuleType('frappe.utils')
        utils.now = lambda: '2026-10-28 12:00:00'
        order = ['project_name', 'project_type', 'custom_abbreviation']
        frappe.get_all.side_effect = [
            [types.SimpleNamespace(name='hidden-override')],
            [types.SimpleNamespace(name='project-order', value=json.dumps(order))]]
        spec = importlib.util.spec_from_file_location('abbreviation_repair_test',
            Path(__file__).parents[1] / 'contractor/patches/project_abbreviation.py')
        service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': frappe, field_module.__name__: field_module,
                'frappe.utils': utils}):
            spec.loader.exec_module(service)
            service.execute()
        field = field_module.create_custom_fields.call_args.args[0]['Project'][0]
        self.assertEqual(field['label'], 'Project Abbreviation')
        self.assertEqual(field['permlevel'], 0)
        self.assertEqual(field['hidden'], 0)
        frappe.delete_doc.assert_called_once_with('Property Setter', 'hidden-override')
        updates = frappe.db.set_value.call_args_list
        self.assertEqual(json.loads(updates[0].args[3]),
                         ['project_name', 'custom_abbreviation', 'project_type'])
        self.assertEqual(updates[1].args[:3], ('DocType', 'Project', 'modified'))
        frappe.clear_cache.assert_called_once_with(doctype='Project')
