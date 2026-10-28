import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from test_tender_project_mapping import Record


class BOQQuantityMigrationTest(unittest.TestCase):
    def test_migration_marks_history_without_resaving_or_repricing(self):
        fake = MagicMock()
        fake.get_meta.return_value.get_field.return_value = None
        fake.get_all.return_value = [Record(name='BOQ-OLD', total_cost=23, project_qty=100)]
        spec = importlib.util.spec_from_file_location('boq_migration_test',
            Path(__file__).parents[1] / 'contractor/patches/boq_project_quantities.py')
        service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe':fake}):
            spec.loader.exec_module(service)
            service.execute()
        fake.db.set_value.assert_called_once_with('BOQ','BOQ-OLD',
            {'quantity_basis':'Per Unit','unit_cost':23,'project_total_cost':2300}, update_modified=False)
        fake.get_doc.assert_not_called()
        fake.db.sql.assert_not_called()
        self.assertEqual(fake.reload_doc.call_count,5)
        self.assertNotIn('total_cost',fake.db.set_value.call_args.args[2])
