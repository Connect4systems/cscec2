"""Ensure optional legacy fields are not required for tender notes."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class DocumentWithoutLegacyFields:
    def get(self, key, default=None):
        return getattr(self, key, default)


class CostingNoteControllerTest(unittest.TestCase):
    def test_tender_lifecycle_without_opportunity_or_order_fields(self):
        frappe = types.ModuleType('frappe')
        document = types.ModuleType('frappe.model.document')
        document.Document = DocumentWithoutLegacyFields
        pricing = types.ModuleType('contractor.tender_pricing')
        pricing.validate_note = MagicMock()
        pricing.apply_note = MagicMock()
        names = types.ModuleType('contractor.project_names')
        names.fill_project_name = MagicMock()
        spec = importlib.util.spec_from_file_location('costing_controller_under_test',
            Path(__file__).parents[1] / 'contractor/contractor_app/doctype/costing_note/costing_note.py')
        controller = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': frappe, 'frappe.model.document': document,
                                     'contractor.tender_pricing': pricing, 'contractor.project_names': names}):
            spec.loader.exec_module(controller)
            note = controller.CostingNote()
            note.tender_analysis = 'TA-1'
            self.assertFalse(hasattr(note, 'opportunity'))
            note.validate()
            pricing.validate_note.assert_called_once_with(note)
            note.on_submit()
            pricing.apply_note.assert_called_once_with(note)
            note.before_cancel()
            note.on_cancel()
            self.assertEqual(note.ignore_linked_doctypes, ['BOQ'])
            pricing.apply_note.assert_called_with(note, cancel=True)
