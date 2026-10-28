import unittest
from contractor.master_data import load_records, ordered_cost_codes, COST_TYPES


class MasterDataTest(unittest.TestCase):
    def test_workbook_hierarchy_and_types(self):
        rows = ordered_cost_codes(load_records('cost_codes.json'))
        self.assertEqual(len(rows), 870)
        seen = set()
        for row in rows:
            if row.get('parent_cost_code'):
                self.assertIn(row['parent_cost_code'], seen)
            seen.add(row['cost_code'])
        self.assertEqual({r['cost_type'] for r in rows if r.get('cost_type')},
                         {f'{title} - C' for title in COST_TYPES})

    def test_bad_hierarchies_rejected(self):
        for rows in ([{'cost_code': 'A', 'parent_cost_code': 'missing'}],
                     [{'cost_code': 'A'}, {'cost_code': 'A'}],
                     [{'cost_code': 'A', 'is_group': 1, 'parent_cost_code': 'B'},
                      {'cost_code': 'B', 'is_group': 1, 'parent_cost_code': 'A'}]):
            with self.assertRaises(ValueError):
                ordered_cost_codes(rows)

    def test_divisions_unique_and_complete(self):
        rows = load_records('divisions.json')
        self.assertEqual(len({r['title'] for r in rows}), 32)
        self.assertEqual(rows[2]['title'], '03 - Concrete')
        self.assertEqual(rows[-1]['title'], '32 - Exterior Improvements')

class CompanyMappingTest(unittest.TestCase):
    def test_types_remap_without_changing_source(self):
        from contractor.master_data import remap_cost_type
        for title in COST_TYPES:
            row = {'cost_type': f'{title} - C'}
            self.assertEqual(remap_cost_type(row, 'CSCEC')['cost_type'], f'{title} - CSCEC')
            self.assertEqual(row['cost_type'], f'{title} - C')
        self.assertEqual(remap_cost_type({'cost_code': 'A'}, 'CSCEC'), {'cost_code': 'A'})

    def test_company_resolution(self):
        import sys
        from unittest.mock import MagicMock, patch
        from contractor.master_data import resolve_company
        frappe = MagicMock()
        frappe.throw.side_effect = ValueError
        frappe.db.get_single_value.return_value = 'System Company'
        frappe.db.get_value.return_value = 'SYS'
        with patch.dict(sys.modules, {'frappe': frappe}):
            self.assertEqual(resolve_company(), ('System Company', 'SYS'))
            frappe.get_all.assert_not_called()
            self.assertEqual(resolve_company('Explicit Company'), ('Explicit Company', 'SYS'))
            frappe.db.get_single_value.return_value = None
            frappe.get_all.return_value = ['Only Company']
            self.assertEqual(resolve_company(), ('Only Company', 'SYS'))
            frappe.get_all.return_value = ['Company A', 'Company B']
            with self.assertRaises(ValueError):
                resolve_company()
