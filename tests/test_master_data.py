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
