import unittest

from contractor.project_contract_rules import require_submitted_costing, contract_totals


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

    def test_totals_tax_discount_deductions_and_base_currency(self):
        rows = self.details()
        tax = Row(charge_type='On Net Total', rate=10)
        actual = Row(charge_type='Actual', tax_amount=5)
        deduction = Row(percent=5)
        totals = contract_totals(rows, [tax, actual], [deduction], discount=10, conversion_rate=2)
        self.assertEqual(totals['total'], 130)
        self.assertEqual(totals['net_total'], 120)
        self.assertEqual(totals['grand_total'], 137)
        self.assertEqual(totals['base_grand_total'], 274)
        self.assertAlmostEqual(totals['net_payable'], 130.15)
        self.assertEqual(rows[0].get('amount'), 130)
        self.assertEqual(contract_totals(rows, [tax, actual], [deduction], 10, 2), totals)

    def test_invalid_quantity_discount_or_conversion_rejected(self):
        rows = self.details()
        for discount, conversion in [(131, 1), (0, 0), (0, float('nan'))]:
            with self.assertRaises(ValueError):
                contract_totals(rows, [], [], discount, conversion)
        rows[1].set('qty', 0)
        with self.assertRaisesRegex(ValueError, 'quantity'):
            contract_totals(rows, [], [])
