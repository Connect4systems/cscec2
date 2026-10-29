"""Clause templates do not need a legacy header Item association."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

from test_tender_pricing import Row


ROOT = Path(__file__).parents[1]


class ClausePricingFieldsTest(unittest.TestCase):
    def load(self, relative, frappe):
        spec = importlib.util.spec_from_file_location(
            'clause_fields_' + Path(relative).stem, ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': frappe}):
            spec.loader.exec_module(module)
        return module

    def test_template_resource_costs_work_without_header_item(self):
        frappe = MagicMock()
        document = MagicMock()
        document.Document = Row
        with patch.dict(sys.modules, {'frappe.model.document': document}):
            module = self.load(
                'contractor/contractor_app/doctype/template_boq/template_boq.py', frappe)
        template = module.TemplateBOQ(material_costs=[Row(item='RESOURCE-1', qty=2, cost=5)])
        template.validate()
        self.assertEqual(template.total_cost, 10)
        self.assertEqual(template.material_costs[0].item, 'RESOURCE-1')
        frappe.throw.assert_not_called()

    def test_metadata_patch_does_not_resave_business_records(self):
        frappe = MagicMock()
        module = self.load('contractor/patches/clause_pricing_fields.py', frappe)
        module.execute()
        self.assertEqual(frappe.reload_doc.call_count, 3)
        frappe.reload_doc.assert_any_call('contractor_app', 'doctype', 'template_boq', force=True)
        frappe.get_doc.assert_not_called()
        frappe.db.set_value.assert_not_called()
        frappe.clear_cache.assert_called_once_with()
