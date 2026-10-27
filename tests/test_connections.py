import importlib
import json
from pathlib import Path
import unittest

from contractor.connections import dashboard_data


class ConnectionDashboardTest(unittest.TestCase):
    def schema(self, doctype):
        slug = doctype.lower().replace(' ', '_')
        path = Path(__file__).parents[1] / 'contractor/contractor_app/doctype' / slug / (slug+'.json')
        return json.loads(path.read_text())

    def field(self, doctype, fieldname):
        return next(f for f in self.schema(doctype)['fields'] if f['fieldname']==fieldname)

    def test_costing_note_boq_count_uses_real_parent_reference(self):
        data = dashboard_data('Costing Note')
        field = self.field('BOQ', data['fieldname'])
        self.assertEqual(field['fieldtype'], 'Link')
        self.assertEqual(field['options'], 'Costing Note')
        self.assertNotIn('BOQ', data['internal_links'])
        self.assertIn('BOQ', [item for group in data['transactions'] for item in group['items']])

    def test_upstream_connections_resolve_to_actual_link_fields(self):
        for doctype in ['Project Offer', 'Project Contract']:
            data = dashboard_data(doctype)
            for target, path in data['internal_links'].items():
                if isinstance(path, str):
                    field = self.field(doctype, path)
                else:
                    table, column = path
                    child_type = self.field(doctype, table)['options']
                    field = self.field(child_type, column)
                self.assertEqual(field['fieldtype'], 'Link')
                self.assertEqual(field['options'], target)
            self.assertIn('Tender Analysis', data['internal_links'])
            self.assertEqual(data['internal_links']['Costing Note'], ['clauses', 'costing_note'])
        self.assertEqual(dashboard_data('Project Contract')['internal_links']['Project Offer'], 'project_offer')

    def test_dashboard_modules_load_fresh_data_and_do_not_duplicate_metadata_groups(self):
        for name in ['Costing Note', 'Project Offer', 'Project Contract']:
            slug = name.lower().replace(' ', '_')
            module = importlib.import_module(f'contractor.contractor_app.doctype.{slug}.{slug}_dashboard')
            data = module.get_data()
            for link in self.schema(name).get('links', []):
                group = next(g for g in data['transactions'] if g['label']==link['group'])
                self.assertEqual(group['items'].count(link['link_doctype']), 1)
            data['transactions'].clear()
            self.assertTrue(module.get_data()['transactions'])
