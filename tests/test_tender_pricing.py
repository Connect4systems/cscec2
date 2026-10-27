"""Pricing lifecycle checks with an in-memory Frappe boundary.

These exercise the application service, not database or framework behavior.
"""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class Row(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__

    def precision(self, field):
        return 6

    def db_set(self, field, value, **kwargs):
        self[field] = value


class PricingLifecycleTest(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType('frappe')
        fake.whitelist = lambda: lambda fn: fn
        fake.db = MagicMock()
        fake.db.exists.return_value = None
        fake.get_doc = MagicMock()
        fake.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
        utils = types.ModuleType('frappe.utils')
        utils.flt = lambda value, precision=None: round(float(value or 0), precision) if precision is not None else float(value or 0)
        utils.today = lambda: '2026-10-27'
        spec = importlib.util.spec_from_file_location('pricing_under_test', Path(__file__).parents[1] / 'contractor/tender_pricing.py')
        self.service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': fake, 'frappe.utils': utils}):
            spec.loader.exec_module(self.service)
        self.fake = fake
        self.target = Row(name='source-1', contractual_clause='CC-1', qty=3, rate=7, applied_costing_note=None)
        self.tender = types.SimpleNamespace(clauses=[self.target], check_permission=MagicMock(), save=MagicMock())
        self.fake.get_doc.return_value = self.tender
        self.row = Row(source_row='source-1', contractual_clause='CC-1', qty=3, target_selling_price=10, is_group=0)
        self.note = types.SimpleNamespace(name='CN-1', tender_analysis='TA-1', costing_note_items=[self.row])

    def test_submit_and_cancel_restore_prior_rate(self):
        self.service.apply_note(self.note)
        self.assertEqual(self.target.rate, 3.333333)
        self.assertEqual(self.target.applied_costing_note, 'CN-1')
        self.assertEqual(self.row.previous_rate, 7)
        self.service.apply_note(self.note, cancel=True)
        self.assertEqual(self.target.rate, 7)
        self.assertIsNone(self.target.applied_costing_note)

    def test_new_note_cannot_overwrite_owned_prices(self):
        self.target.applied_costing_note = 'CN-OTHER'
        with self.assertRaisesRegex(ValueError, 'previous Costing Note'):
            self.service.apply_note(self.note)
        self.tender.save.assert_not_called()

    def test_series_and_titles_are_not_used_to_match_prices(self):
        self.target.series_number = '9_12'
        self.row.series_number = '1_1'
        self.service.apply_note(self.note)
        self.assertEqual(self.target.rate, 3.333333)
        self.target.qty = 4
        with self.assertRaisesRegex(ValueError, 'source clause has changed'):
            self.service.apply_note(self.note, cancel=True)

    def test_cancel_cannot_reverse_a_different_notes_prices(self):
        self.service.apply_note(self.note)
        self.target.applied_costing_note = 'CN-OTHER'
        with self.assertRaisesRegex(ValueError, 'no longer owns'):
            self.service.apply_note(self.note, cancel=True)

    def test_boq_cannot_change_submitted_costing_note(self):
        self.note.docstatus = 1
        self.note.check_permission = MagicMock()
        self.fake.get_doc.return_value = self.note
        boq = types.SimpleNamespace(costing_note='CN-1')
        with self.assertRaisesRegex(ValueError, 'Cancel or amend'):
            self.service.update_from_boq(boq)

    def test_boq_save_writes_link_to_its_costing_note_row(self):
        self.fake.db.get_value.return_value = Row(parent='CN-1', parenttype='Costing Note', boq_reference=None)
        boq = Row(name='BOQ-1', costing_note='CN-1', line_id='row-1')
        self.service.sync_boq_reference(boq)
        self.fake.db.set_value.assert_called_once_with('Costing Note Items', 'row-1', 'boq_reference', 'BOQ-1', update_modified=False)

    def test_boq_link_cannot_point_at_another_notes_row(self):
        self.fake.db.get_value.return_value = Row(parent='CN-OTHER', parenttype='Costing Note')
        with self.assertRaisesRegex(ValueError, 'valid Costing Note row'):
            self.service.sync_boq_reference(Row(name='BOQ-1', costing_note='CN-1', line_id='row-1'))
        self.fake.db.set_value.assert_not_called()

    def test_cancellation_only_clears_its_own_boq_link(self):
        row = Row(parent='CN-1', parenttype='Costing Note', boq_reference='BOQ-NEW')
        self.fake.db.get_value.return_value = row
        boq = Row(name='BOQ-OLD', costing_note='CN-1', line_id='row-1')
        self.service.sync_boq_reference(boq, remove=True)
        self.fake.db.set_value.assert_not_called()
        row.boq_reference = 'BOQ-OLD'
        self.service.sync_boq_reference(boq, remove=True)
        self.fake.db.set_value.assert_called_once_with('Costing Note Items', 'row-1', 'boq_reference', None, update_modified=False)

    def test_tender_boq_link_matches_clause_and_applied_costing_note(self):
        self.tender.name = 'TA-1'
        self.fake.get_all = MagicMock(return_value=[
            Row(name='BOQ-OTHER', contractual_clause='CC-OTHER', costing_note='CN-1'),
            Row(name='BOQ-NEW', contractual_clause='CC-1', costing_note='CN-NEW'),
            Row(name='BOQ-APPLIED', contractual_clause='CC-1', costing_note='CN-1')])
        self.assertEqual(self.service.submitted_boq_links(self.tender), {'source-1': 'BOQ-NEW'})
        self.target.applied_costing_note = 'CN-1'
        self.assertEqual(self.service.submitted_boq_links(self.tender), {'source-1': 'BOQ-APPLIED'})
        self.assertEqual(self.fake.get_all.call_args.kwargs['filters']['docstatus'], 1)

    def test_tender_group_or_cancelled_boq_has_no_link(self):
        self.tender.name = 'TA-1'
        self.fake.get_all = MagicMock(return_value=[])
        self.assertEqual(self.service.submitted_boq_links(self.tender), {})
        self.target.is_group = 1
        self.fake.get_all.return_value = [Row(name='BOQ-1', contractual_clause='CC-1')]
        self.assertEqual(self.service.submitted_boq_links(self.tender), {})


if __name__ == '__main__':
    unittest.main()
