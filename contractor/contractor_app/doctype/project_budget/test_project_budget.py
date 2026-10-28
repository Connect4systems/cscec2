"""Run on a migrated Frappe site: bench --site SITE run-tests --doctype 'Project Budget'."""
import unittest

try:
    import frappe
    from frappe.tests.utils import FrappeTestCase
except ModuleNotFoundError:
    frappe = None
    FrappeTestCase = unittest.TestCase


@unittest.skipUnless(frappe, 'Requires a migrated Frappe site')
class TestProjectBudget(FrappeTestCase):
    def test_native_resource_children_and_budget_snapshot_use_project_quantities(self):
        from contractor.boq_quantities import calculate_resources, unit_costs
        from contractor.project_budget_rules import build_budget
        boq = frappe.new_doc('BOQ')
        boq.quantity_basis = 'Project Quantity'
        boq.project_qty = 100
        boq.append('material_costs', dict(per_unit_qty=2, cost=5))
        boq.validate()
        self.assertEqual(boq.material_costs[0].qty, 200)
        self.assertEqual(boq.total_cost, 1000)
        clauses = [dict(name='group', is_group=1, series_number='1', clause_title='Civil'),
            dict(name='detail', series_number='1_1', clause_title='Concrete', qty=150)]
        rows, totals = build_budget(clauses, {'detail': unit_costs(boq)})
        budget = frappe.new_doc('Project Budget')
        budget.set('clauses', rows)
        budget.update(totals)
        self.assertEqual(budget.total_project_budget, 1500)
        self.assertEqual(budget.clauses[1].material_budget, 1500)
        self.assertEqual(budget.clauses[0].total_cost, 1500)
        self.assertEqual(budget.clauses[1].qty, 150)
        self.assertEqual(budget.meta.get_field('clauses').options, 'Project Budget Clause')
        self.assertEqual(budget.clauses[1].meta.get_field('unit_cost').read_only, 1)

    def test_historical_per_unit_boq_normalizes_to_same_budget_unit_cost(self):
        from contractor.boq_quantities import calculate_resources, unit_costs
        boq = frappe.new_doc('BOQ')
        boq.quantity_basis = 'Per Unit'
        boq.project_qty = 100
        boq.append('material_costs', dict(qty=2, cost=5))
        calculate_resources(boq)
        self.assertEqual(boq.material_costs[0].qty, 2)
        self.assertEqual(boq.total_cost, 10)
        self.assertEqual(unit_costs(boq)['total_cost'], 10)
