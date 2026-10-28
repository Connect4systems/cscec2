import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class ProjectCleanupPatchTest(unittest.TestCase):
    def patch_module(self, fields_exist=False):
        fake = MagicMock()
        fake.get_meta.return_value.has_field.return_value = fields_exist
        def get_value(doctype, name, *args, **kwargs):
            if doctype == 'Custom Field':
                return 'Opportunity Item-is_group' if name == {'dt': 'Opportunity Item', 'fieldname': 'is_group'} else None
            if doctype == 'Property Setter':
                field, prop = ('item', 'label') if name == 'BOQ ID-item-label' else ('naming_series', 'options')
                return types.SimpleNamespace(doc_type='BOQ ID', field_name=field, property=prop)
        fake.db.get_value.side_effect = get_value
        cleanup = types.ModuleType('contractor.app_cleanup')
        cleanup.retire_unused_doctypes = MagicMock(return_value=[])
        spec = importlib.util.spec_from_file_location('cycle_cleanup_test', Path(__file__).parents[1] / 'contractor/patches/cleanup_project_cycle.py')
        service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': fake, 'contractor.app_cleanup': cleanup}):
            spec.loader.exec_module(service)
            service.execute()
        return fake

    def test_only_stale_setters_removed_and_custom_field_data_preserved(self):
        fake = self.patch_module()
        self.assertEqual([call.args for call in fake.delete_doc.call_args_list],
            [('Property Setter', 'BOQ ID-item-label'), ('Property Setter', 'BOQ ID-naming_series-options')])
        fake.db.set_value.assert_called_once_with('Custom Field', 'Opportunity Item-is_group',
            {'hidden': 1, 'in_list_view': 0, 'reqd': 0})
        fake.db.delete.assert_not_called()
        fake.db.sql.assert_not_called()

    def test_site_specific_target_fields_preserve_their_property_setters(self):
        fake = self.patch_module(fields_exist=True)
        fake.delete_doc.assert_not_called()

    def test_fixture_exports_exclude_retired_fields_and_requested_features_stay(self):
        import json
        root = Path(__file__).parents[1]
        exported = json.loads((root / 'contractor/fixtures/custom_field.json').read_text())
        retired = json.loads((root / 'contractor/patches/retired_cycle_fields.json').read_text())
        active_pairs = {(row['dt'], row['fieldname']) for row in exported}
        self.assertFalse(active_pairs.intersection((row['dt'], row['fieldname']) for row in retired))
        namespace = {}
        exec((root / 'contractor/hooks.py').read_text().replace('from . import __version__ as app_version', 'app_version="test"'), namespace)
        names = namespace['fixtures'][0]['filters'][0][2]
        self.assertEqual(set(names), {row['name'] for row in exported})
        self.assertEqual(namespace['doctype_js']['Comparison'], 'public/js/doctype/comparison_table.js')
        self.assertIn('Subcontractor Custody', namespace['override_doctype_class'])
        for slug in ('comparison', 'supplier_comparison', 'item_coding_request', 'item_code',
                     'subcontractor_custody', 'subcontractor_custody_item'):
            self.assertTrue((root / 'contractor/contractor_app/doctype' / slug / (slug + '.json')).exists())
        self.assertTrue((root / 'contractor/report/account_balances/account_balances.py').exists())
