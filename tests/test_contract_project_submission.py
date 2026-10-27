import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class Document:
    def get(self, field, default=None):
        return getattr(self, field, default)


class ContractProjectSubmissionTest(unittest.TestCase):
    def test_only_contract_submission_creates_project(self):
        fake = types.ModuleType('frappe')
        document = types.ModuleType('frappe.model.document')
        document.Document = Document
        utils = types.ModuleType('frappe.utils')
        utils.getdate = lambda value: value
        utils.flt = lambda value: float(value or 0)
        contracts = types.ModuleType('contractor.project_contract')
        contracts.require_ready = MagicMock()
        taxes = types.ModuleType('contractor.project_contract_taxes')
        for name in ('calculate_contract_taxes', 'get_sales_tax_template', 'validate_template'):
            setattr(taxes, name, MagicMock())
        projects = types.ModuleType('contractor.contract_projects')
        projects.create_project = MagicMock(return_value={'project': 'PROJ-1'})
        modules = {'frappe': fake, 'frappe.model.document': document, 'frappe.utils': utils,
            'contractor.project_contract': contracts, 'contractor.project_contract_taxes': taxes,
            'contractor.contract_projects': projects}
        spec = importlib.util.spec_from_file_location('contract_submission_under_test',
            Path(__file__).parents[1] / 'contractor/contractor_app/doctype/project_contract/project_contract.py')
        service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(service)
            contract = service.ProjectContract()
            contract.name = 'PC-1'
            contract.doctype = 'Project Contract'
            contract.on_submit()
            self.assertEqual(contract.created_project, 'PROJ-1')
            projects.create_project.assert_called_once_with('PC-1')
            offer = service.ProjectContract()
            offer.doctype = 'Project Offer'
            offer.on_submit()
            projects.create_project.assert_called_once()
