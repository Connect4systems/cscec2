import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from test_subcontract_workflow import Doc


class ProjectBudgetServiceTest(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType('frappe')
        self.frappe.whitelist = lambda: lambda fn: fn
        self.frappe.throw = MagicMock(side_effect=ValueError)
        self.frappe.db = MagicMock()
        self.frappe.db.get_value.return_value = None
        self.frappe.get_all = MagicMock(return_value=[])
        utils = types.ModuleType('frappe.utils')
        utils.today = lambda: '2026-10-28'
        self.group = Doc(name='contract-group', source_row='tender-group', is_group=1,
            series_number='4', clause_title='Civil', contractual_clause='CC-G')
        self.detail = Doc(name='contract-detail', source_row='tender-detail', is_group=0,
            series_number='4_7', clause_title='Concrete', contractual_clause='CC-D', qty=150,
            uom='m3', costing_note='CN-1', submitted_boq='BOQ-1')
        self.contract = Doc(name='PC-1', docstatus=1, created_project='PROJ-1', company='Company',
            currency='EGP', tender_analysis='TA-1', title='Hospital', clauses=[self.group, self.detail])
        self.project = Doc(name='PROJ-1', project_contract='PC-1', company='Company', status='Open')
        self.tender = Doc(name='TA-1', company='Company', currency='EGP', clauses=[
            Doc(name='tender-group', contractual_clause='CC-G', is_group=1),
            Doc(name='tender-detail', contractual_clause='CC-D', is_group=0)])
        self.note_row = Doc(name='note-row', source_row='tender-detail', contractual_clause='CC-D',
            is_group=0, cost=23, qty=100, uom='m3')
        self.note = Doc(name='CN-1', docstatus=1, tender_analysis='TA-1', currency='EGP', costing_note_items=[self.note_row])
        self.boq = Doc(name='BOQ-1', docstatus=1, tender_analysis='TA-1', costing_note='CN-1',
            line_id='note-row', contractual_clause='CC-D', unit='m3', quantity_basis='Project Quantity',
            project_qty=100, total_material_costs=1000, total_labor_costs=1000,
            total_contractors=300, total_expenses=0, custom_total_equipment_costs=0, total_cost=2300)
        self.docs = {('Project Contract','PC-1'):self.contract, ('Project','PROJ-1'):self.project,
            ('Tender Analysis','TA-1'):self.tender, ('Costing Note','CN-1'):self.note, ('BOQ','BOQ-1'):self.boq}
        self.frappe.get_doc = MagicMock(side_effect=lambda doctype, name: self.docs[(doctype,name)])
        self.budget = Doc(name='BUDGET-1', doctype='Project Budget', docstatus=0,
            project_contract='PC-1', clauses=[], is_new=lambda: True)
        self.frappe.new_doc = MagicMock(return_value=self.budget)
        spec = importlib.util.spec_from_file_location('budget_service_test', Path(__file__).parents[1] / 'contractor/project_budget.py')
        self.service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': self.frappe, 'frappe.utils': utils}):
            spec.loader.exec_module(self.service)

    def create(self):
        # Model Frappe's child document conversion rather than plain list assignment.
        original_set = self.budget.set
        def set_value(field, value):
            original_set(field, [Doc(**row) for row in value] if field == 'clauses' else value)
        self.budget.set = set_value
        return self.service.create_budget('PC-1')

    def test_create_uses_contract_qty_and_submitted_exact_sources(self):
        result = self.create()['doc']
        self.assertEqual(result.total_project_budget, 3450)
        self.assertEqual(result.total_material, 1500)
        self.assertEqual(result.project, 'PROJ-1')
        self.assertEqual(result.clauses[1].qty, 150)
        self.assertEqual(result.clauses[1].unit_cost, 23)
        self.assertEqual(result.clauses[1].costing_note_row, 'note-row')
        self.assertEqual(result.clauses[1].boq, 'BOQ-1')
        self.assertFalse(result.clauses[1].get('name'))
        self.assertEqual(self.boq.total_cost, 2300)

    def test_existing_active_budget_is_reused(self):
        self.frappe.db.get_value.return_value = 'BUDGET-existing'
        self.docs[('Project Budget','BUDGET-existing')] = Doc()
        self.assertEqual(self.service.create_budget('PC-1'), {'existing':'BUDGET-existing'})
        self.frappe.new_doc.assert_not_called()

    def test_sources_must_be_submitted_and_correctly_linked(self):
        for record, field, bad in [(self.contract,'docstatus',0), (self.note,'docstatus',0),
                (self.boq,'docstatus',2), (self.boq,'line_id','OTHER'),
                (self.note,'tender_analysis','OTHER'), (self.boq,'unit','kg')]:
            previous = record.get(field)
            record.set(field,bad)
            with self.assertRaises(ValueError): self.service.create_budget('PC-1')
            record.set(field,previous)

    def test_wrong_project_and_currency_are_rejected(self):
        self.project.project_contract = 'OTHER'
        with self.assertRaises(ValueError): self.service.create_budget('PC-1')
        self.project.project_contract = 'PC-1'
        self.note.currency = 'USD'
        with self.assertRaises(ValueError): self.service.create_budget('PC-1')

    def test_ambiguous_boq_fallback_is_not_latest_selected(self):
        self.detail.submitted_boq = None
        self.frappe.get_all.return_value = ['BOQ-1', 'BOQ-2']
        with self.assertRaises(ValueError): self.service.create_budget('PC-1')

    def test_duplicate_active_budget_blocks_save(self):
        self.create()
        self.frappe.db.get_value.return_value = 'OTHER-BUDGET'
        with self.assertRaises(ValueError): self.service.validate_budget(self.budget)

    def test_save_recalculates_tampered_amounts_and_keeps_child_identity(self):
        self.create()
        row = self.budget.clauses[1]
        row.name = 'saved-child'
        row.total_cost = 1
        row.unit_cost = 999
        self.service.validate_budget(self.budget)
        self.assertIs(row, self.budget.clauses[1])
        self.assertEqual(row.name,'saved-child')
        self.assertEqual(row.total_cost,3450)
        self.assertEqual(row.unit_cost,23)
        self.assertEqual(self.budget.total_project_budget,3450)

    def test_existing_snapshot_does_not_silently_adopt_changed_source_cost(self):
        self.create()
        before = Doc(project_contract='PC-1', clauses=[Doc(**row.as_dict()) for row in self.budget.clauses])
        self.budget.get_doc_before_save = lambda: before
        self.boq.total_material_costs = 1100
        self.boq.total_cost = 2400
        self.note_row.cost = 24
        with self.assertRaises(ValueError): self.service.validate_budget(self.budget)
        self.assertEqual(self.budget.total_project_budget,3450)

    def test_submit_sets_status_and_cancelled_previous_budget_allows_new_one(self):
        self.create()
        self.budget.docstatus = 1
        self.service.validate_budget(self.budget)
        self.assertEqual(self.budget.status,'Submitted')
        filters = self.frappe.db.get_value.call_args.args[1]
        self.assertEqual(filters['docstatus'],['!=',2])
