import unittest

from contractor.tender_logic import number_rows, price_rows


class DocumentRow:
    """Model Frappe's get/set interface without dictionary subscripting."""
    def __init__(self, values):
        self.values = dict(values)

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class TenderRulesTest(unittest.TestCase):
    def rows(self):
        return [dict(clause_title='Civil', is_group=1),
                dict(clause_title='Concrete', qty=2, cost=10, default_profit_margin=20),
                dict(clause_title='Excavation', qty=3, cost=5),
                dict(clause_title='Electrical', is_group=1),
                dict(clause_title='Cable', qty=1.5, cost=4)]

    def test_numbering_rebuilds_after_reorder_and_deletion(self):
        rows = self.rows()
        number_rows(rows)
        self.assertEqual([r['series_number'] for r in rows], ['1', '1_1', '1_2', '2', '2_1'])
        rows[1], rows[2] = rows[2], rows[1]
        del rows[1]
        number_rows(rows)
        self.assertEqual([r['series_number'] for r in rows], ['1', '1_1', '2', '2_1'])

    def test_excel_preserves_gaps_and_validates_parent(self):
        rows = self.rows()[:3]
        for row, series in zip(rows, ['4', '4_2', '4_9']):
            row['series_number'] = series
        number_rows(rows, 'From Excel')
        self.assertEqual(rows[2]['series_number'], '4_9')
        rows[2]['series_number'] = '5_1'
        with self.assertRaisesRegex(ValueError, 'preceding group'):
            number_rows(rows, 'From Excel')

    def test_duplicate_excel_rejected(self):
        rows = self.rows()[:3]
        for row, series in zip(rows, ['1', '1_1', '1_1']):
            row['series_number'] = series
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            number_rows(rows, 'From Excel')

    def test_detail_requires_group_and_positive_quantity(self):
        with self.assertRaisesRegex(ValueError, 'add a group'):
            number_rows([dict(clause_title='Orphan', qty=1)])
        rows = self.rows()
        rows[1]['qty'] = 0
        with self.assertRaisesRegex(ValueError, 'quantity'):
            number_rows(rows)

    def test_group_totals_do_not_double_count_or_retain_old_values(self):
        rows = self.rows()
        number_rows(rows)
        self.assertEqual(price_rows(rows), (41, 45))
        self.assertEqual(rows[0]['target_selling_price'], 39)
        self.assertEqual(rows[3]['target_selling_price'], 6)
        rows[1]['cost'] = 20
        self.assertEqual(price_rows(rows), (61, 69))
        self.assertEqual(price_rows(rows), (61, 69))

    def test_document_rows_number_and_price_without_item_assignment(self):
        rows = [DocumentRow(row) for row in self.rows()]
        number_rows(rows)
        self.assertEqual([r.get('series_number') for r in rows], ['1', '1_1', '1_2', '2', '2_1'])
        self.assertEqual(rows[1].get('parent_series'), '1')
        self.assertEqual(price_rows(rows), (41, 45))
        self.assertEqual(rows[0].get('target_selling_price'), 39)
        self.assertEqual(price_rows(rows), (41, 45))

    def test_excel_series_preserved_for_document_rows_on_save(self):
        rows = [DocumentRow(dict(clause_title='Group', is_group=1, series_number='7')),
                DocumentRow(dict(clause_title='Detail', qty=2, series_number='7_5'))]
        number_rows(rows, 'From Excel')
        self.assertEqual(rows[1].get('series_number'), '7_5')
        self.assertEqual(rows[1].get('parent_series'), '7')


if __name__ == '__main__':
    unittest.main()
