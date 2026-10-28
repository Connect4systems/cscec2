import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).parents[1]


class CRContractTypesTest(unittest.TestCase):
    def test_cr_links_to_contract_type_without_item_group_filter(self):
        schema = json.loads((ROOT / 'contractor/contractor_app/doctype/cr/cr.json').read_text())
        field = next(f for f in schema['fields'] if f['fieldname'] == 'contract_type')
        self.assertEqual(field['options'], 'Contract Type')
        self.assertFalse(field.get('link_filters'))

    def test_seed_preserves_historical_names_and_skips_existing_types(self):
        frappe = MagicMock()
        frappe.get_all.side_effect = [[types.SimpleNamespace(contract_type='Legacy Civil')], []]
        frappe.db.exists.side_effect = lambda dt, name: name == 'Civil'
        spec = importlib.util.spec_from_file_location('cr_types_test', ROOT / 'contractor/patches/cr_contract_types.py')
        service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': frappe}):
            spec.loader.exec_module(service)
            service.execute()
        self.assertEqual(service.CONTRACT_TYPES, ('Arch', 'Civil', 'Elec', 'Mech', 'Service'))
        created = {call.args[0]['title'] for call in frappe.get_doc.call_args_list}
        self.assertEqual(created, {'Arch', 'Elec', 'Mech', 'Service', 'Legacy Civil'})
