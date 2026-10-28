import unittest
from contractor.boq_quantities import calculate_resources, unit_costs
from test_tender_pricing import Row


class BOQProjectQuantityTest(unittest.TestCase):
    def boq(self):
        return Row(name='BOQ-1', quantity_basis='Project Quantity', project_qty=100,
            material_costs=[Row(per_unit_qty=2, cost=5)], labor_costs=[Row(per_unit_qty=0.5, cost=20)],
            contractors_table=[Row(per_unit_qty=1, cost=3)], expenses_table=[], custom_equipment=[])

    def test_full_project_quantities_and_category_costs(self):
        doc = self.boq()
        calculate_resources(doc)
        self.assertEqual(doc.material_costs[0].qty, 200)
        self.assertEqual(doc.labor_costs[0].qty, 50)
        self.assertEqual(doc.total_material_costs, 1000)
        self.assertEqual(doc.total_labor_costs, 1000)
        self.assertEqual(doc.total_contractors, 300)
        self.assertEqual(doc.total_cost, 2300)
        self.assertEqual(doc.project_total_cost, 2300)
        self.assertEqual(doc.unit_cost, 23)
        self.assertEqual(unit_costs(doc)['total_material_costs'], 10)

    def test_recalculate_and_quantity_changes_do_not_multiply_twice(self):
        doc = self.boq()
        calculate_resources(doc)
        calculate_resources(doc)
        self.assertEqual(doc.total_cost, 2300)
        doc.project_qty = 150
        calculate_resources(doc)
        self.assertEqual(doc.material_costs[0].qty, 300)
        self.assertEqual(doc.total_cost, 3450)
        self.assertEqual(doc.unit_cost, 23)

    def test_old_submitted_basis_remains_unit_cost(self):
        doc = Row(quantity_basis='Per Unit', project_qty=100,
            material_costs=[Row(qty=2, cost=5)])
        calculate_resources(doc)
        self.assertEqual(doc.material_costs[0].qty, 2)
        self.assertEqual(doc.total_cost, 10)
        self.assertEqual(doc.project_total_cost, 1000)
        self.assertEqual(unit_costs(doc)['total_cost'], 10)

    def test_old_draft_conversion_preserves_coefficients_and_unit_price(self):
        doc = Row(quantity_basis='Per Unit', project_qty=100,
            material_costs=[Row(qty=2, per_unit_qty=1, cost=5)])
        calculate_resources(doc, convert_legacy=True)
        self.assertEqual(doc.quantity_basis, 'Project Quantity')
        self.assertEqual(doc.material_costs[0].per_unit_qty, 2)
        self.assertEqual(doc.material_costs[0].qty, 200)
        self.assertEqual(doc.total_cost, 1000)
        self.assertEqual(doc.unit_cost, 10)

    def test_project_budget_normalizes_then_scales_to_final_contract_quantity(self):
        from contractor.project_budget_rules import build_budget
        doc = self.boq()
        calculate_resources(doc)
        clauses = [dict(name='g', is_group=1, series_number='1', clause_title='Group'),
            dict(name='d', series_number='1_1', clause_title='Detail', qty=150)]
        rows, totals = build_budget(clauses, {'d': unit_costs(doc)})
        self.assertEqual(rows[1]['unit_cost'], 23)
        self.assertEqual(totals['total_project_budget'], 3450)
        self.assertEqual(totals['total_material'], 1500)

    def test_invalid_project_quantity_coefficients_and_rates_rejected(self):
        for qty in (0, -1, float('nan')):
            doc = self.boq()
            doc.project_qty = qty
            with self.assertRaises(ValueError): calculate_resources(doc)
        for field in ('per_unit_qty', 'cost'):
            doc = self.boq()
            doc.material_costs[0][field] = -1
            with self.assertRaises(ValueError): calculate_resources(doc)


    def test_equipment_table_totals_flow_to_budget_without_duplicate_legacy_alias(self):
        from contractor.project_budget_rules import build_budget
        doc = self.boq()
        doc.equipment_costs = [Row(per_unit_qty=0.25, cost=40)]
        calculate_resources(doc)
        calculate_resources(doc)
        self.assertEqual(doc.equipment_costs[0].qty,25)
        self.assertEqual(doc.total_equipment_costs,1000)
        self.assertEqual(doc.total_cost,3300)
        self.assertEqual(doc.unit_cost,33)
        clauses = [dict(name='g',is_group=1,series_number='1',clause_title='Group'),
            dict(name='d',series_number='1_1',clause_title='Detail',qty=150)]
        _, totals = build_budget(clauses,{'d':unit_costs(doc)})
        self.assertEqual(totals['total_equipment'],1500)
        self.assertEqual(totals['total_project_budget'],4950)

    def test_new_and_existing_equipment_rows_are_each_counted_once(self):
        doc = self.boq()
        doc.equipment_costs = [Row(per_unit_qty=0.25,cost=40)]
        doc.custom_equipment = [Row(per_unit_qty=0.5,cost=10)]
        calculate_resources(doc)
        calculate_resources(doc)
        self.assertEqual(doc.total_equipment_costs,1500)
        self.assertEqual(unit_costs(doc)['total_equipment_costs'],15)
        self.assertEqual(doc.total_cost,3800)
