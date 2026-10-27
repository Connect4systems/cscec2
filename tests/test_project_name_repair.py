import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class Doc(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__

    def check_permission(self, permission):
        pass


def load_module(filename, modules):
    spec = importlib.util.spec_from_file_location('repair_under_test_'+Path(filename).stem,
        Path(__file__).parents[1] / filename)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


class ProjectNameRepairTest(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType('frappe')
        fake.whitelist = lambda: lambda fn: fn
        fake.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
        self.docs = {
            ('Tender Analysis', 'TA-1'): Doc(doctype='Tender Analysis', project='Hospital'),
            ('Costing Note', 'CN-1'): Doc(doctype='Costing Note', project='', tender_analysis='TA-1'),
            ('Project Offer', 'POF-1'): Doc(doctype='Project Offer', project='Negotiated project', tender_analysis='TA-1'),
        }
        fake.get_doc = MagicMock(side_effect=lambda doctype, name: self.docs[(doctype, name)])
        self.fake = fake
        self.service = load_module('contractor/project_names.py', {'frappe': fake})

    def test_old_boq_fills_from_blank_note_then_tender(self):
        boq = Doc(doctype='BOQ', project='', costing_note='CN-1')
        self.assertEqual(self.service.fill_project_name(boq), 'Hospital')
        self.assertEqual(boq.project, 'Hospital')

    def test_manual_value_is_never_overwritten(self):
        doc = Doc(doctype='Project Offer', project='Manual project', tender_analysis='TA-1')
        self.assertEqual(self.service.fill_project_name(doc), 'Manual project')
        self.fake.get_doc.assert_not_called()

    def test_contract_prefers_offer_value_over_tender(self):
        doc = Doc(doctype='Project Contract', project='', project_offer='POF-1', tender_analysis='TA-1')
        self.assertEqual(self.service.fill_project_name(doc), 'Negotiated project')

    def test_existing_project_is_authoritative_for_missing_contract_text(self):
        self.docs[('Project', 'PROJ-1')] = Doc(doctype='Project', project_name='Existing project')
        doc = Doc(doctype='Project Contract', project='', created_project='PROJ-1', tender_analysis='TA-1')
        self.assertEqual(self.service.fill_project_name(doc), 'Existing project')

    def test_metadata_patch_forces_reload_and_preserves_layout_fields(self):
        fake = types.ModuleType('frappe')
        fake.reload_doc = MagicMock()
        fake.clear_cache = MagicMock()
        fake.db = MagicMock()
        fake.delete_doc = MagicMock()
        order = ['title', 'tender_number', 'custom_user_field', 'connections_tab']
        def get_all(doctype, **kwargs):
            if (doctype == 'Property Setter' and kwargs['filters'].get('doc_type') == 'Tender Analysis'
                    and kwargs['filters'].get('property') == 'field_order'):
                return [Doc(name='order-setter', value=json.dumps(order))]
            return []
        fake.get_all = get_all
        utils = types.ModuleType('frappe.utils')
        utils.now = lambda: '2026-10-27 19:00:00'
        names = types.ModuleType('contractor.project_names')
        names.fill_project_name = MagicMock()
        modules = {'frappe': fake, 'frappe.utils': utils, 'contractor.project_names': names}
        module = load_module('contractor/patches/repair_project_name_flow.py', modules)
        with patch.dict(sys.modules, modules):
            module.execute()
        self.assertEqual(fake.reload_doc.call_count, 6)
        self.assertTrue(all(call.kwargs['force'] for call in fake.reload_doc.call_args_list))
        setter = next(call for call in fake.db.set_value.call_args_list if call.args[0]=='Property Setter')
        result = json.loads(setter.args[3])
        self.assertIn('project', result)
        self.assertIn('custom_user_field', result)
