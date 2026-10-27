import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, create_autospec, patch


def frappe_v15_rename_doc(doctype, old, new, force=False, merge=False, *,
        ignore_if_exists=False, show_alert=True, rebuild_search=True):
    """Public Frappe 15.110.0 signature, including keyword validation."""


class ClearanceMigrationTest(unittest.TestCase):
    def module(self, existing):
        fake = types.ModuleType('frappe')
        fake.db = MagicMock()
        fake.db.exists.side_effect = lambda doctype, name: name in existing
        fake.db.has_column.return_value = False
        fake.throw = lambda text: (_ for _ in ()).throw(ValueError(text))
        fake.rename_doc = create_autospec(frappe_v15_rename_doc)
        path = Path(__file__).parents[1]/'contractor/patches/rename_clearnce_doctypes.py'
        spec = importlib.util.spec_from_file_location('rename_under_test', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': fake}):
            spec.loader.exec_module(module)
        return module, fake

    def test_renames_existing_parents_and_marks_legacy_without_merging(self):
        module, fake = self.module({'Clearence', 'Purchase Clearence'})
        module.execute()
        self.assertEqual(fake.rename_doc.call_count, 2)
        self.assertEqual(fake.rename_doc.call_args_list[0].args, ('DocType', 'Clearence', 'Project Clearnce'))
        self.assertTrue(all(call.kwargs['force'] for call in fake.rename_doc.call_args_list))
        self.assertTrue(any('legacy_record=1' in call.args[0] for call in fake.db.sql.call_args_list))

    def test_retry_after_unsupported_keyword_reuses_existing_legacy_column(self):
        module, fake = self.module({'Clearence', 'Purchase Clearence'})
        fake.db.has_column.return_value = True
        module.execute()
        self.assertEqual(fake.rename_doc.call_count, 2)
        self.assertFalse(any('alter table' in call.args[0] for call in fake.db.sql.call_args_list))

    def test_retry_after_first_rename_only_processes_remaining_parent(self):
        module, fake = self.module({'Project Clearnce', 'Purchase Clearence'})
        module.execute()
        fake.rename_doc.assert_called_once_with('DocType', 'Purchase Clearence', 'Subcontract Clearnce',
            force=True, show_alert=False)

    def test_conflict_in_second_target_blocks_all_renames(self):
        module, fake = self.module({'Clearence', 'Purchase Clearence', 'Subcontract Clearnce'})
        with self.assertRaisesRegex(ValueError, 'Both'):
            module.execute()
        fake.rename_doc.assert_not_called()
        fake.db.sql.assert_not_called()

    def test_purchasing_hooks_and_project_price_fields_are_retired(self):
        root = Path(__file__).parents[1]
        namespace = {}
        exec((root/'contractor/hooks.py').read_text().replace('from . import __version__ as app_version','app_version="test"'), namespace)
        self.assertNotIn('Purchase Order', namespace['override_doctype_class'])
        self.assertNotIn('Purchase Order', namespace['doctype_js'])
        self.assertNotIn('Purchase Invoice', namespace['doctype_js'])
        schema = json.loads((root/'contractor/contractor_app/doctype/project_clause/project_clause.json').read_text())
        self.assertFalse(any(field['fieldtype']=='Currency' for field in schema['fields']))
        exported = json.loads((root/'contractor/contractor_app/custom/project.json').read_text(encoding='utf-8'))
        fields = {field['fieldname']: field for field in exported['custom_fields']}
        self.assertNotIn('project_contract_total', fields)
        self.assertEqual(fields['project_clause_groups']['options'], 'Project Clause Summary')
        self.assertTrue(fields['project_contract_currency']['hidden'])
        self.assertFalse((root/'contractor/contractor_app/doctype/clearence/clearence.json').exists())
        self.assertFalse((root/'contractor/contractor_app/doctype/purchase_clearence/purchase_clearence.json').exists())
