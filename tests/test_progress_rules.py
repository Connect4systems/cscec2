import unittest
from contractor.progress_rules import certificate_quantity, project_clause_values, update_quantities


class Row(dict):
    def set(self, field, value):
        self[field] = value


class ProgressRulesTest(unittest.TestCase):
    def test_project_snapshot_excludes_all_monetary_values(self):
        row = Row(qty=100, rate=5, amount=500, base_amount=500, net_rate=5, net_amount=500, clause_title='Work')
        self.assertEqual(project_clause_values(row), {'qty': 100, 'clause_title': 'Work'})

    def test_current_period_quantities_cannot_exceed_remaining(self):
        self.assertEqual(certificate_quantity(100, 30, 20), 50)
        with self.assertRaisesRegex(ValueError, 'remaining'):
            certificate_quantity(100, 80, 21)
        for qty in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                certificate_quantity(100, 0, qty)

    def test_customer_and_subcontract_execution_are_separate(self):
        rows = [Row(name='g', is_group=1, series_number='1', clause_title='Civil'),
                Row(name='a', qty=100, uom='m', is_group=0), Row(name='b', qty=20, uom='m3', is_group=0)]
        summary = update_quantities(rows, {'a': 30}, {'a': 40, 'b': 5})
        self.assertEqual(rows[1]['completed_qty'], 30)
        self.assertEqual(rows[1]['subcontract_completed_qty'], 40)
        self.assertEqual(rows[1]['remaining_qty'], 70)
        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[0]['qty'], 100)
        self.assertEqual(summary[1]['qty'], 20)
        # Cancellation of the last certificate clears, rather than retaining, progress.
        update_quantities(rows, {}, {})
        self.assertEqual(rows[1]['completed_qty'], 0)
        self.assertEqual(rows[1]['completion_percentage'], 0)

    def test_same_unit_group_totals_aggregate_once(self):
        rows = [Row(name='g', is_group=1, series_number='1', clause_title='Civil'),
                Row(name='a', qty=10, uom='m'), Row(name='b', qty=30, uom='m')]
        summary = update_quantities(rows, {'a': 5, 'b': 15}, {})
        self.assertEqual(summary[0]['qty'], 40)
        self.assertEqual(summary[0]['completed_qty'], 20)
        self.assertEqual(summary[0]['completion_percentage'], 50)
