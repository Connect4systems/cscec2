import unittest
from contractor.cr_clause_selection import select_project_rows


class ProjectClauseSelectionTest(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(name='g1', is_group=1, series_number='4'),
            dict(name='a', parent_series='4', series_number='4_2'),
            dict(name='b', parent_series='4', series_number='4_7'),
            dict(name='g2', is_group=1, series_number='8'),
            dict(name='c', parent_series='8', series_number='8_3')]

    def test_all_preserves_rows(self):
        self.assertEqual(select_project_rows(self.rows), self.rows)

    def test_selection_adds_groups_and_keeps_source_order(self):
        result = select_project_rows(self.rows, False, ['c', 'b', 'b'])
        self.assertEqual([r['name'] for r in result], ['g1', 'b', 'g2', 'c'])
        self.assertEqual(result[1]['series_number'], '4_7')

    def test_multiple_details_do_not_duplicate_heading(self):
        result = select_project_rows(self.rows, False, ['b', 'a'])
        self.assertEqual([r['name'] for r in result], ['g1', 'a', 'b'])

    def test_reject_empty_unknown_group_and_malformed_selection(self):
        for selection in ([], ['unknown'], ['g1'], 'a', None, [{}]):
            with self.assertRaises(ValueError):
                select_project_rows(self.rows, False, selection)

class SelectedQuantitiesTest(unittest.TestCase):
    def test_accepts_positive_decimal_quantity(self):
        from contractor.cr_clause_selection import selected_quantities
        rows = [{'name': 'heading', 'is_group': 1}, {'name': 'detail', 'qty': 10}]
        self.assertEqual(selected_quantities(rows, {'detail': '2.5'}), {'detail': 2.5})
        self.assertEqual(rows[1]['qty'], 10)
        self.assertEqual(selected_quantities(rows), {})

    def test_rejects_invalid_quantities_and_unselected_rows(self):
        from contractor.cr_clause_selection import selected_quantities
        rows = [{'name': 'heading', 'is_group': 1}, {'name': 'detail'}]
        for quantities in ({'detail': 0}, {'detail': -1}, {'detail': 'NaN'},
                           {'detail': float('inf')}, {'detail': ''}, {'detail': True},
                           {'missing': 3}, {'heading': 3}, []):
            with self.assertRaises(ValueError):
                selected_quantities(rows, quantities)
