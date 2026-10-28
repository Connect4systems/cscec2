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

class MergeProjectClausesTest(unittest.TestCase):
    def test_merge_keeps_edits_skips_duplicates_and_inserts_under_group(self):
        from contractor.cr_clause_selection import merge_project_clauses
        from contractor.tender_logic import number_rows
        group = dict(project_clause='g1', is_group=1, series_number='4', clause_title='Civil')
        existing_detail = dict(project_clause='a', series_number='4_2', parent_series='4', qty=2.5, clause_title='Edited A')
        second_group = dict(project_clause='g2', is_group=1, series_number='8', clause_title='Electrical')
        existing = [group, existing_detail, second_group]
        incoming = [dict(group), dict(project_clause='a', parent_series='4', series_number='4_2', qty=10),
            dict(project_clause='b', parent_series='4', series_number='4_7', qty=3, clause_title='B')]
        merged = merge_project_clauses(existing, incoming)
        self.assertEqual([row['project_clause'] for row in merged], ['g1', 'a', 'b', 'g2'])
        self.assertIs(merged[1], existing_detail)
        self.assertEqual(merged[1]['qty'], 2.5)
        self.assertEqual(merged[1]['clause_title'], 'Edited A')
        number_rows(merged, 'From Excel')
        again = merge_project_clauses(merged, incoming)
        self.assertEqual(again, merged)

    def test_manual_rows_keep_series_when_new_source_group_collides(self):
        from contractor.cr_clause_selection import merge_project_clauses
        from contractor.tender_logic import number_rows
        existing = [dict(is_group=1, series_number='1', clause_title='Manual'),
            dict(series_number='1_1', parent_series='1', clause_title='Manual detail', qty=2)]
        incoming = [dict(project_clause='g', is_group=1, series_number='1', clause_title='Project group'),
            dict(project_clause='a', parent_series='1', series_number='1_1', clause_title='Project detail', qty=3)]
        merged = merge_project_clauses(existing, incoming)
        self.assertEqual([row['series_number'] for row in merged], ['1', '1_1', '2', '2_1'])
        self.assertIs(merged[0], existing[0])
        number_rows(merged, 'From Excel')
