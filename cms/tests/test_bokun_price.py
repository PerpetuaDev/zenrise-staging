import unittest
from cms import bokun_price

CATS = [{'id': 1, 'title': 'Adult'}, {'id': 2, 'title': 'Child'}, {'id': 3, 'title': 'Infant'}]


def avail(units):
    return [{'pricesByRate': [{'activityRateId': 9, 'pricePerCategoryUnit': units}]}]


def unit(cat_id, amount, mn=None, mx=None):
    return {'id': cat_id, 'amount': {'amount': float(amount), 'currency': 'JPY'},
            'minParticipantsRequired': mn, 'maxParticipantsRequired': mx}


class TestRows(unittest.TestCase):
    def test_maps_category_ids_to_titles(self):
        r = bokun_price.rows(avail([unit(1, 12000, 1, 6), unit(2, 10000, 1, 6)]), CATS)
        self.assertEqual([(x['category'], x['amount']) for x in r],
                         [('Adult', 12000), ('Child', 10000)])

    def test_unknown_category_id_yields_none_category(self):
        r = bokun_price.rows(avail([unit(99, 5000)]), CATS)
        self.assertIsNone(r[0]['category'])

    def test_reads_only_the_first_slot_with_prices(self):
        a = [{'pricesByRate': []}] + avail([unit(1, 21000, 3, 3)])
        self.assertEqual(bokun_price.rows(a, CATS)[0]['amount'], 21000)

    def test_empty_availability_is_empty(self):
        self.assertEqual(bokun_price.rows([], CATS), [])


class TestFromPrice(unittest.TestCase):
    def test_ikebana_takes_the_lowest_adult_tier(self):
        r = bokun_price.rows(avail([unit(1, 44000, 1, 2), unit(1, 21000, 3, 3),
                                    unit(1, 21000, 4, 4)]), CATS)
        self.assertEqual(bokun_price.from_price(r),
                         {'amount': 21000, 'currency': 'JPY', 'category': 'Adult'})

    def test_ignores_cheaper_child_and_infant_rows(self):
        r = bokun_price.rows(avail([unit(1, 12000, 1, 6), unit(2, 10000, 1, 6),
                                    unit(3, 0, 1, 6)]), CATS)
        self.assertEqual(bokun_price.from_price(r)['amount'], 12000)

    def test_falls_back_to_lowest_of_any_category_when_no_adult(self):
        r = bokun_price.rows(avail([unit(2, 10000), unit(3, 4000)]), CATS)
        self.assertEqual(bokun_price.from_price(r),
                         {'amount': 4000, 'currency': 'JPY', 'category': 'Infant'})

    def test_unpriced_product_is_none(self):
        self.assertIsNone(bokun_price.from_price([]))


class TestFormat(unittest.TestCase):
    def test_english_from_price_per_adult(self):
        fp = {'amount': 21000, 'currency': 'JPY', 'category': 'Adult'}
        self.assertEqual(bokun_price.format_from(fp, 'en'), 'from ¥21,000 per adult')

    def test_japanese_from_price_per_adult(self):
        fp = {'amount': 21000, 'currency': 'JPY', 'category': 'Adult'}
        self.assertEqual(bokun_price.format_from(fp, 'ja'), '¥21,000〜（大人おひとり）')

    def test_drops_per_adult_when_there_is_no_adult_category(self):
        fp = {'amount': 4000, 'currency': 'JPY', 'category': 'Child'}
        self.assertEqual(bokun_price.format_from(fp, 'en'), 'from ¥4,000')
        self.assertEqual(bokun_price.format_from(fp, 'ja'), '¥4,000〜')

    def test_unpriced_formats_empty(self):
        self.assertEqual(bokun_price.format_from(None, 'en'), '')

    def test_full_breakdown_lists_category_and_tier(self):
        r = bokun_price.rows(avail([unit(1, 44000, 1, 2), unit(1, 21000, 3, 6)]), CATS)
        self.assertEqual(bokun_price.format_full(r, 'en'),
                         ['Adult, 1–2 guests: ¥44,000', 'Adult, 3–6 guests: ¥21,000'])

    def test_full_breakdown_omits_tier_when_unbounded(self):
        r = bokun_price.rows(avail([unit(1, 23000)]), CATS)
        self.assertEqual(bokun_price.format_full(r, 'en'), ['Adult: ¥23,000'])


if __name__ == '__main__':
    unittest.main()
