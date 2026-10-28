import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from test_tender_project_mapping import Record


class BOQEquipmentMigrationTest(unittest.TestCase):
    def execute(self, existing=False):
        fake = MagicMock()
        meta = MagicMock()
        meta.get_field.return_value = Record(options='Existing Equipment') if existing else None
        meta.has_field.side_effect = lambda name: existing and name == 'custom_total_equipment_costs'
        child = MagicMock()
        child.istable = 1
        child.has_field.return_value = True
        fake.get_meta.side_effect = lambda name: meta if name == 'BOQ' else child
        fake.db.get_value.return_value = None
        fake.db.exists.return_value = False
        def get_all(doctype, **kwargs):
            if doctype == 'BOQ': return [Record(name='BOQ-OLD', custom_total_equipment_costs=50)]
            if doctype == 'Existing Equipment': return [Record(parent='BOQ-OLD', qty=2, cost=25)]
            return []
        fake.get_all.side_effect = get_all
        utils = types.ModuleType('frappe.utils')
        utils.now = lambda: '2026-10-28 12:00:00'
        spec = importlib.util.spec_from_file_location('equipment_migration_test',
            Path(__file__).parents[1] / 'contractor/patches/boq_equipment.py')
        service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe':fake, 'frappe.utils':utils}):
            spec.loader.exec_module(service)
            service.execute()
        return fake

    def test_new_equipment_metadata_installed_without_business_record_resaves(self):
        fake = self.execute()
        self.assertEqual([call.args[2] for call in fake.reload_doc.call_args_list],
            ['boq_equipment_cost','boq','template_boq'])
        fake.get_doc.assert_not_called()
        fake.db.delete.assert_not_called()
        fake.db.sql.assert_not_called()

    def test_existing_equipment_totals_preserved_without_copying_or_repricing(self):
        fake = self.execute(existing=True)
        calls = [call for call in fake.db.set_value.call_args_list if call.args[0] == 'BOQ']
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0].args,('BOQ','BOQ-OLD','total_equipment_costs',50))
        self.assertFalse(calls[0].kwargs['update_modified'])
        fake.get_doc.assert_not_called()
        fake.db.delete.assert_not_called()
