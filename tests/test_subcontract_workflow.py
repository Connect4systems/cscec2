import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from test_tender_project_mapping import Record


class Doc(Record):
    def update(self, values):
        self.__dict__.update(values)

    def as_dict(self):
        return dict(self.__dict__)

    def append(self, field, row):
        child = Doc(**row)
        getattr(self, field).append(child)
        return child

    def precision(self, field):
        return 2

    def get_doc_before_save(self):
        return None


class SubcontractWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType('frappe')
        self.frappe.whitelist = lambda: lambda fn: fn
        self.frappe.throw = MagicMock(side_effect=ValueError)
        self.frappe.db = MagicMock()
        self.frappe.get_doc = MagicMock()
        self.frappe.new_doc = MagicMock()
        self.frappe.get_all = MagicMock(return_value=[])
        self.frappe.get_cached_value = MagicMock(return_value='EGP')
        utils = types.ModuleType('frappe.utils')
        utils.flt = lambda value, *args: float(value or 0)
        utils.today = lambda: '2026-10-28'
        self.progress = types.ModuleType('contractor.project_progress')
        self.progress.CERTIFICATES = ('Project Clearnce', 'Subcontract Clearnce')
        self.progress.executed_quantities = MagicMock(return_value={})
        self.progress.refresh_project = MagicMock()
        self.modules = {'frappe': self.frappe, 'frappe.utils': utils,
            'contractor.project_progress': self.progress}
        self.patcher = patch.dict(sys.modules, self.modules)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.service = self.load('subcontracting')

    def load(self, module):
        spec = importlib.util.spec_from_file_location(module + '_test',
            Path(__file__).parents[1] / ('contractor/' + module + '.py'))
        service = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(service)
        return service

    def source(self):
        return Doc(name='CR-1', docstatus=1, project='PROJ-1', supplier='SUP-1',
            contract_type='Civil', posting_date='2026-10-28', end_date='2026-12-31',
            attach_cr='/private/cr.pdf', note='Terms', numbering_mode='From Excel',
            clauses=[Doc(name='cr-row', is_group=1, clause_title='Civil', series_number='4')])

    def contract(self):
        return Doc(name='SCC-1', docstatus=1, project='PROJ-1', supplier='SUP-1', company='Company',
            currency='EGP', conversion_rate=1, delivery_date='2026-12-31', clauses=[
                Doc(name='heading', is_group=1, series_number='4', clause_title='Civil'),
                Doc(name='detail', is_group=0, series_number='4_7', parent_series='4',
                    clause_title='Concrete', qty=10, rate=25, uom='m3')])

    def project(self):
        return Doc(name='PROJ-1', status='Open', project_name='Hospital', company='Company', project_clauses=[])

    def certificate(self):
        return Doc(name=None, doctype='Subcontract Clearnce', docstatus=0,
            subcontractor_contract='SCC-1', project='PROJ-1', supplier='SUP-1', company='Company',
            currency='EGP', conversion_rate=1, clauses=[Doc(idx=1, subcontractor_contract_clause='detail', qty=3)])

    def test_mapping_copies_cr_values_and_uses_new_child_identities(self):
        source = self.source()
        target = Doc(clauses=[])
        self.frappe.get_doc.return_value = source
        self.frappe.new_doc.return_value = target
        self.frappe.db.get_value.side_effect = [None, 'Company']
        result = self.service.create_contract('CR-1')
        self.assertEqual(result.cr, 'CR-1')
        self.assertEqual(result.supplier, 'SUP-1')
        self.assertEqual(result.delivery_date, source.end_date)
        self.assertEqual(result.attach_cr, source.attach_cr)
        self.assertEqual(result.note, source.note)
        self.assertEqual(result.clauses[0].source_cr_row, 'cr-row')
        self.assertFalse(result.clauses[0].get('name'))
        self.assertEqual(result.clauses[0].series_number, '4')

    def test_unsubmitted_cr_cannot_create_contract(self):
        source = self.source()
        source.docstatus = 0
        self.frappe.get_doc.return_value = source
        with self.assertRaises(ValueError):
            self.service.create_contract('CR-1')
        self.frappe.new_doc.assert_not_called()

    def test_existing_contract_reused(self):
        self.frappe.get_doc.return_value = self.source()
        self.frappe.db.get_value.return_value = 'SCC-existing'
        self.assertEqual(self.service.create_contract('CR-1'), {'existing': 'SCC-existing'})
        self.frappe.new_doc.assert_not_called()

    def test_direct_contract_totals_and_submitted_rate_validation(self):
        contract = self.contract()
        self.frappe.get_doc.return_value = self.project()
        self.service.validate_contract(contract)
        self.assertEqual(contract.contract_amount, 250)
        self.assertEqual(contract.clauses[0].amount, 250)
        contract.clauses[1].rate = 0
        with self.assertRaises(ValueError):
            self.service.validate_contract(contract)

    def test_clearance_maps_supplier_rates_and_starts_at_zero(self):
        contract = self.contract()
        project = self.project()
        self.frappe.get_doc.side_effect = [contract, project]
        self.frappe.new_doc.return_value = Doc(name=None, clauses=[])
        result = self.service.create_clearance('SCC-1')
        self.assertEqual(result.subcontractor_contract, 'SCC-1')
        self.assertEqual(result.supplier, 'SUP-1')
        self.assertEqual(result.clauses[1].subcontractor_contract_clause, 'detail')
        self.assertEqual(result.clauses[1].qty, 0)
        self.assertEqual(result.clauses[1].rate, 25)
        self.assertEqual(result.clauses[1].remaining_qty, 10)

    def test_unsubmitted_contract_cannot_create_clearance(self):
        contract = self.contract()
        contract.docstatus = 0
        self.frappe.get_doc.return_value = contract
        with self.assertRaises(ValueError):
            self.service.create_clearance('SCC-1')
        self.frappe.new_doc.assert_not_called()

    def test_contract_previous_qty_and_rate_are_enforced(self):
        doc = self.certificate()
        doc.clauses[0].rate = 999
        self.frappe.get_all.side_effect = [['CERT-1'], [Doc(subcontractor_contract_clause='detail', qty=2)]]
        self.assertTrue(self.service.set_contract_quantities(doc, self.project(), self.contract()))
        self.assertEqual(doc.clauses[0].previous_qty, 2)
        self.assertEqual(doc.clauses[0].remaining_qty, 5)
        self.assertEqual(doc.clauses[0].total_executed_qty, 5)
        self.assertEqual(doc.clauses[0].rate, 25)
        filters = self.frappe.get_all.call_args_list[0].kwargs['filters']
        self.assertNotIn('name', filters)  # unsaved documents must still count submitted certificates

    def test_contract_and_project_quantity_caps(self):
        for contract_qty, project_qty, previous in [(2, 20, 0), (10, 4, 2)]:
            doc = self.certificate()
            contract = self.contract()
            contract.clauses[1].qty = contract_qty
            contract.clauses[1].project_clause = 'project-row'
            project = self.project()
            project.project_clauses = [Doc(name='project-row', qty=project_qty)]
            self.progress.executed_quantities.return_value = {'project-row': previous}
            with self.assertRaises(ValueError):
                self.service.set_contract_quantities(doc, project, contract)

    def test_supplier_mismatch_and_duplicate_clause_blocked(self):
        doc = self.certificate()
        doc.supplier = 'OTHER'
        with self.assertRaises(ValueError):
            self.service.set_contract_quantities(doc, self.project(), self.contract())
        doc.supplier = 'SUP-1'
        doc.clauses.append(Doc(idx=2, subcontractor_contract_clause='detail', qty=1))
        with self.assertRaises(ValueError):
            self.service.set_contract_quantities(doc, self.project(), self.contract())

    def test_contract_clearance_uses_shared_tax_and_validation_flow(self):
        certificate = self.certificate()
        certificate.deductions = []
        certificate.taxes = []
        contract = self.contract()
        project = self.project()
        self.frappe.get_doc.side_effect = [contract, project, contract, project]
        taxes = types.ModuleType('contractor.project_contract_taxes')
        def calculate(doc):
            doc.grand_total = sum(row.qty * row.rate for row in doc.clauses if not row.is_group)
        taxes.calculate_contract_taxes = MagicMock(side_effect=calculate)
        with patch.dict(sys.modules, {'contractor.subcontracting': self.service,
                'contractor.project_contract_taxes': taxes}):
            clearances = self.load('project_clearances')
            clearances.validate_clearance(certificate)
        taxes.calculate_contract_taxes.assert_called_once_with(certificate)
        self.assertEqual(certificate.net_payable, 75)
        self.assertEqual(certificate.status, 'Draft')
        self.assertEqual(certificate.clauses[0].remaining_qty, 7)

    def test_linked_contract_requires_submitted_matching_cr_and_blocks_duplicates(self):
        contract = self.contract()
        contract.cr = 'CR-1'
        source = self.source()
        source.docstatus = 0
        self.frappe.get_doc.side_effect = [self.project(), source]
        with self.assertRaises(ValueError):
            self.service.validate_contract(contract)
        source.docstatus = 1
        source.supplier = 'OTHER'
        self.frappe.get_doc.side_effect = [self.project(), source]
        with self.assertRaises(ValueError):
            self.service.validate_contract(contract)
        source.supplier = 'SUP-1'
        self.frappe.get_doc.side_effect = [self.project(), source]
        self.frappe.get_all.return_value = ['SCC-existing']
        with self.assertRaises(ValueError):
            self.service.validate_contract(contract)

    def test_project_picker_filters_submitted_contracts_and_supplier_permissions(self):
        self.frappe.get_doc.return_value = self.project()
        self.frappe.has_permission = MagicMock()
        self.frappe.get_list = MagicMock(side_effect=[
            [Doc(name='C1', supplier='S1'), Doc(name='C2', supplier='S1'), Doc(name='C3', supplier='S2')],
            [Doc(name='S1', supplier_name='Supplier One')]])
        result = self.service.project_contract_options('PROJ-1')
        self.assertEqual([row.name for row in result['contracts']], ['C1', 'C2'])
        self.assertEqual([row.name for row in result['suppliers']], ['S1'])
        first = self.frappe.get_list.call_args_list[0]
        self.assertEqual(first.args[0], 'Subcontractor Contract')
        self.assertEqual(first.kwargs['filters']['project'], 'PROJ-1')
        self.assertEqual(first.kwargs['filters']['docstatus'], 1)
        self.frappe.has_permission.assert_called_once_with('Subcontract Clearnce', 'create', throw=True)

    def test_empty_project_picker_does_not_offer_unrelated_suppliers(self):
        self.frappe.get_doc.return_value = self.project()
        self.frappe.has_permission = MagicMock()
        self.frappe.get_list = MagicMock(return_value=[])
        self.assertEqual(self.service.project_contract_options('PROJ-1'), {'suppliers': [], 'contracts': []})
        self.frappe.get_list.assert_called_once()

    def test_project_action_rejects_contract_from_another_project_or_supplier(self):
        for values in ({'project': 'OTHER'}, {'project': 'PROJ-1', 'supplier': 'OTHER'}):
            self.frappe.get_doc.side_effect = [self.contract(), self.project()]
            with self.assertRaises(ValueError):
                self.service.create_clearance('SCC-1', **values)
        self.frappe.new_doc.assert_not_called()
