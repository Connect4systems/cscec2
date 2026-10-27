import unittest

from contractor.project_contract_rules import require_submitted_costing, apply_deductions


class Row:
    def __init__(self, **values):
        self.values = values

    def get(self, field, default=None):
        return self.values.get(field, default)

    def set(self, field, value):
        self.values[field] = value


class ProjectContractRulesTest(unittest.TestCase):
    def details(self):
        return [Row(is_group=1), Row(contractual_clause='CC-1', applied_costing_note='CN-1', qty=2, rate=50),
                Row(contractual_clause='CC-2', applied_costing_note='CN-1', qty=3, rate=10)]

    def test_ready_requires_all_active_notes_submitted(self):
        rows = self.details()
        with self.assertRaisesRegex(ValueError, 'Submit all'):
            require_submitted_costing(rows, [])
        with self.assertRaisesRegex(ValueError, 'Submit all'):
            require_submitted_costing(rows, [dict(name='CN-1', docstatus=1), dict(name='CN-2', docstatus=0)])
        require_submitted_costing(rows, [dict(name='CN-1', docstatus=1)])

    def test_unpriced_clause_blocks_contract(self):
        rows = self.details()
        rows[2].set('applied_costing_note', None)
        with self.assertRaisesRegex(ValueError, 'Every detail clause'):
            require_submitted_costing(rows, [dict(name='CN-1', docstatus=1)])

    def test_group_only_tender_cannot_create_contract(self):
        with self.assertRaisesRegex(ValueError, 'detail clause'):
            require_submitted_costing([Row(is_group=1)], [dict(name='CN-1', docstatus=1)])

    def test_deductions_use_native_grand_total_and_base_currency(self):
        deduction = Row(percent=5)
        totals = apply_deductions([deduction], grand_total=137, conversion_rate=2)
        self.assertAlmostEqual(totals['total_deductions'], 6.85)
        self.assertAlmostEqual(totals['base_total_deductions'], 13.70)
        self.assertAlmostEqual(totals['net_payable'], 130.15)
        self.assertEqual(apply_deductions([deduction], 137, 2), totals)

    def test_invalid_deduction_or_conversion_rejected(self):
        for percent, conversion in [(101, 1), (-1, 1), (0, 0), (0, float('nan'))]:
            with self.assertRaises(ValueError):
                apply_deductions([Row(percent=percent)], 100, conversion)
        with self.assertRaisesRegex(ValueError, 'Total deductions'):
            apply_deductions([Row(percent=60), Row(percent=60)], 100)
