import unittest

from contractor.project_budget_rules import build_budget


class ProjectBudgetRulesTest(unittest.TestCase):
    def clauses(self):
        return [dict(name='group', is_group=1, series_number='4', clause_title='Civil', qty=999),
            dict(name='detail', is_group=0, series_number='4_7', clause_title='Concrete', qty=100, uom='m3')]

    def boq(self, **values):
        row = dict(name='BOQ-1', total_material_costs=50, total_labor_costs=20,
            total_contractors=10, total_expenses=5, custom_total_equipment_costs=2, total_cost=87)
        row.update(values)
        return row

    def test_final_contract_quantity_scales_every_unit_category_once(self):
        boq = self.boq(project_qty=500)
        rows, totals = build_budget(self.clauses(), {'detail': boq})
        self.assertEqual(rows[1]['unit_cost'], 87)
        self.assertEqual(rows[1]['total_cost'], 8700)
        self.assertEqual(totals, dict(total_project_budget=8700, total_material=5000,
            total_labour=2000, total_subcontractor=1000, total_other_expenses=500, total_equipment=200))
        self.assertEqual(rows[0]['total_cost'], 8700)
        self.assertEqual(rows[0]['qty'], 0)
        self.assertEqual(rows[1]['series_number'], '4_7')
        self.assertEqual(rows[1]['parent_series'], '4')
        self.assertEqual(boq['project_qty'], 500)

    def test_repeated_titles_stay_separate_and_groups_do_not_double_count(self):
        clauses = self.clauses()
        clauses += [dict(name='g2', is_group=1, series_number='8', clause_title='Civil'),
            dict(name='d2', series_number='8_3', clause_title='Concrete', qty=2)]
        rows, totals = build_budget(clauses, {'detail': self.boq(), 'd2': self.boq(name='BOQ-2')})
        self.assertEqual(totals['total_project_budget'], 8874)
        self.assertEqual(rows[2]['total_cost'], 174)
        self.assertEqual([row['contract_clause_row'] for row in rows], ['group','detail','g2','d2'])

    def test_category_rounding_reconciles_with_quantity_times_unit_cost(self):
        clauses = self.clauses()
        clauses[1]['qty'] = 3
        boq = self.boq(total_material_costs='0.335', total_labor_costs='0.335',
            total_contractors=0, total_expenses=0, custom_total_equipment_costs=0, total_cost='0.67')
        rows, totals = build_budget(clauses, {'detail': boq})
        self.assertEqual(rows[1]['total_cost'], 2.01)
        self.assertAlmostEqual(totals['total_material'] + totals['total_labour'], 2.01)
        self.assertGreaterEqual(totals['total_material'], 0)

    def test_invalid_sources_and_nonfinite_numbers_rejected(self):
        for boqs in ({}, {'detail': self.boq(total_cost=999)},
                     {'detail': self.boq(total_material_costs=-1)},
                     {'detail': self.boq(total_expenses=float('nan'))},
                     {'detail': self.boq(total_material_costs='1e1000')}):
            with self.assertRaises(ValueError):
                build_budget(self.clauses(), boqs)
        for qty in (0, -1, float('inf')):
            clauses = self.clauses()
            clauses[1]['qty'] = qty
            with self.assertRaises(ValueError):
                build_budget(clauses, {'detail': self.boq()})

    def test_empty_or_group_only_budget_rejected(self):
        for clauses in ([], self.clauses()[:1]):
            with self.assertRaises(ValueError):
                build_budget(clauses, {})


    def test_selling_rates_amounts_and_profit_margins_do_not_enter_budget(self):
        clauses = self.clauses()
        before_rows, before = build_budget(clauses, {'detail': self.boq()})
        clauses[1].update(rate=999999, amount=99999900, default_profit_margin=800)
        after_rows, after = build_budget(clauses, {'detail': self.boq()})
        self.assertEqual(before, after)
        self.assertEqual(after['total_project_budget'], 8700)
        self.assertEqual(before_rows[1]['total_cost'], after_rows[1]['total_cost'])
