import unittest
from cms import bokun_price

CATS = [{'id': 1, 'title': 'Adult'}, {'id': 2, 'title': 'Child'}, {'id': 3, 'title': 'Infant'}]


def avail(units):
    return [{'pricesByRate': [{'activityRateId': 9, 'pricePerCategoryUnit': units}]}]


def unit(cat_id, amount, mn=None, mx=None):
    return {'id': cat_id, 'amount': {'amount': float(amount), 'currency': 'JPY'},
            'minParticipantsRequired': mn, 'maxParticipantsRequired': mx}


# The Zen Journey's pricing category: titled "Group", but ticketCategory says
# ADULT. This is the trap the group-pricing detection must not fall into.
GROUP_CATS = [{'id': 1238056, 'title': 'Group（1~6）', 'ticketCategory': 'ADULT',
               'occupancy': 6, 'dependent': True}]


def group_rate(rate_id, priced_per_person=False, mn=1, mx=6, title='Group(1~6) Harf Day'):
    return {'id': rate_id, 'title': title,
            'pricedPerPerson': priced_per_person, 'minPerBooking': mn, 'maxPerBooking': mx}


def group_price(rate_id, amount, extra=None):
    return {'activityRateId': rate_id,
            'pricePerBooking': {'amount': float(amount), 'currency': 'JPY'},
            'pricePerCategoryUnit': [],
            'extraPricePerCategoryUnit': extra or []}


def group_avail(rates, prices):
    return [{'rates': rates, 'pricesByRate': prices}]


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
                         {'amount': 21000, 'currency': 'JPY', 'category': 'Adult',
                          'per_booking': False})

    def test_ignores_cheaper_child_and_infant_rows(self):
        r = bokun_price.rows(avail([unit(1, 12000, 1, 6), unit(2, 10000, 1, 6),
                                    unit(3, 0, 1, 6)]), CATS)
        self.assertEqual(bokun_price.from_price(r)['amount'], 12000)

    def test_falls_back_to_lowest_of_any_category_when_no_adult(self):
        r = bokun_price.rows(avail([unit(2, 10000), unit(3, 4000)]), CATS)
        self.assertEqual(bokun_price.from_price(r),
                         {'amount': 4000, 'currency': 'JPY', 'category': 'Infant',
                          'per_booking': False})

    def test_unpriced_product_is_none(self):
        self.assertIsNone(bokun_price.from_price([]))


class TestPluralCategories(unittest.TestCase):
    def test_from_price_with_adults_plural_title(self):
        """Test that 'Adults' (plural) is recognized as adult category for from-price."""
        cats_plural = [{'id': 1, 'title': 'Adults'}, {'id': 2, 'title': 'Child'}]
        r = bokun_price.rows(avail([unit(1, 44000, 1, 2), unit(1, 21000, 3, 6),
                                    unit(2, 10000, 1, 6)]), cats_plural)
        self.assertEqual(bokun_price.from_price(r),
                         {'amount': 21000, 'currency': 'JPY', 'category': 'Adults',
                          'per_booking': False})

    def test_format_from_with_adults_plural_title(self):
        """Test that 'Adults' (plural) still produces 'per adult' wording."""
        fp = {'amount': 21000, 'currency': 'JPY', 'category': 'Adults'}
        self.assertEqual(bokun_price.format_from(fp, 'en'), 'from ¥21,000 per adult')
        self.assertEqual(bokun_price.format_from(fp, 'ja'), '¥21,000〜（大人おひとり）')

    def test_format_full_with_children_plural(self):
        """Test that 'Children' (plural) translates to 子供 in Japanese."""
        cats_plural = [{'id': 1, 'title': 'Adult'}, {'id': 2, 'title': 'Children'}]
        r = bokun_price.rows(avail([unit(2, 8000)]), cats_plural)
        self.assertEqual(bokun_price.format_full(r, 'ja'), ['子供: ¥8,000'])


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


class TestGroupPricing(unittest.TestCase):
    """The Zen Journey model: pricedPerPerson: false + pricePerBooking,
    rather than pricePerCategoryUnit. Its pricing category is titled
    'Group（1~6）' but ticketCategory is 'ADULT' — the detection must not be
    fooled by that."""

    def test_rows_emits_a_per_booking_row(self):
        a = group_avail([group_rate(2536321)],
                         [group_price(2536321, 40000)])
        self.assertEqual(bokun_price.rows(a, GROUP_CATS),
                          [{'category': None, 'min': 1, 'max': 6,
                            'amount': 40000, 'currency': 'JPY', 'per_booking': True,
                            'rate_title': 'Group(1~6) Harf Day'}])

    def test_ticket_category_adult_does_not_make_the_group_row_an_adult_row(self):
        a = group_avail([group_rate(2536321)],
                         [group_price(2536321, 40000)])
        row = bokun_price.rows(a, GROUP_CATS)[0]
        self.assertFalse(bokun_price._is_adult(row))

    def test_extra_price_per_category_unit_never_enters_the_headline_price(self):
        extra = [{'id': 300422, 'prices': [{'id': 1238056,
                                            'amount': {'amount': 10000.0, 'currency': 'JPY'}}]},
                 {'id': 300423, 'prices': [{'id': 1238056,
                                            'amount': {'amount': 20000.0, 'currency': 'JPY'}}]}]
        a = group_avail([group_rate(2536321)],
                         [group_price(2536321, 40000, extra=extra)])
        r = bokun_price.rows(a, GROUP_CATS)
        self.assertEqual([x['amount'] for x in r], [40000])

    def test_priced_per_person_true_is_not_treated_as_group(self):
        a = group_avail([group_rate(2536321, priced_per_person=True)],
                         [group_price(2536321, 40000)])
        self.assertEqual(bokun_price.rows(a, GROUP_CATS), [])

    def test_missing_rate_metadata_is_not_treated_as_group(self):
        """pricePerBooking with no corresponding 'rates' entry (so
        pricedPerPerson is unknown) must not be treated as group pricing --
        the safe default is to skip it, not to price it."""
        a = [{'pricesByRate': [group_price(2536321, 40000)]}]
        self.assertEqual(bokun_price.rows(a, GROUP_CATS), [])

    def test_from_price_picks_the_cheaper_of_two_group_rates(self):
        # The real Zen Journey slot has a Half Day rate (¥40,000) and a Full
        # Day rate (¥70,000); the cheaper one is the headline.
        a = group_avail(
            [group_rate(2536321), group_rate(2536324)],
            [group_price(2536321, 40000), group_price(2536324, 70000)])
        r = bokun_price.rows(a, GROUP_CATS)
        self.assertEqual(bokun_price.from_price(r),
                          {'amount': 40000, 'currency': 'JPY', 'category': None,
                           'per_booking': True})

    def test_format_from_group_english(self):
        fp = {'amount': 40000, 'currency': 'JPY', 'category': None, 'per_booking': True}
        self.assertEqual(bokun_price.format_from(fp, 'en'), 'from ¥40,000 per group')

    def test_format_from_group_japanese(self):
        fp = {'amount': 40000, 'currency': 'JPY', 'category': None, 'per_booking': True}
        self.assertEqual(bokun_price.format_from(fp, 'ja'), '¥40,000〜（1グループ）')

    def test_format_full_includes_the_group_size(self):
        r = [{'category': None, 'min': 1, 'max': 6, 'amount': 40000,
              'currency': 'JPY', 'per_booking': True}]
        self.assertEqual(bokun_price.format_full(r, 'en'), ['Group, 1–6 guests: ¥40,000'])

    def test_no_price_at_all_still_yields_none(self):
        """A product with neither a per-person nor a per-booking price must
        route to the in-preparation layout, not error."""
        a = [{'rates': [group_rate(2536321, priced_per_person=True)],
              'pricesByRate': [{'activityRateId': 2536321, 'pricePerCategoryUnit': []}]}]
        r = bokun_price.rows(a, GROUP_CATS)
        self.assertEqual(r, [])
        self.assertIsNone(bokun_price.from_price(r))

    def test_the_zen_journey_two_rates_are_labelled_by_rate_title_not_both_group(self):
        """The real trap (task 14): two GROUP rates, both bookable through
        the same widget, must not render as two identical 'Group' rows."""
        a = group_avail(
            [group_rate(2536321, title='Group(1~6) Harf Day'),
             group_rate(2536324, title='Group(1~6) Full Day')],
            [group_price(2536321, 40000), group_price(2536324, 70000)])
        r = bokun_price.rows(a, GROUP_CATS)
        self.assertEqual(bokun_price.format_full(r, 'en'),
                          ['Group(1~6) Harf Day: ¥40,000', 'Group(1~6) Full Day: ¥70,000'])

    def test_group_rate_title_is_rendered_verbatim_including_the_clients_typo(self):
        """'Harf' is the client's own typo. It is reported to them, not
        silently corrected here."""
        a = group_avail([group_rate(2536321, title='Group(1~6) Harf Day')],
                         [group_price(2536321, 40000)])
        r = bokun_price.rows(a, GROUP_CATS)
        self.assertIn('Harf', bokun_price.format_full(r, 'en')[0])

    def test_group_rate_title_is_not_translated_on_japanese_pages(self):
        """Bokun only has rate titles in English (spec: deliberately not in
        scope to fix here), so the Japanese breakdown shows the English
        title verbatim rather than a translated or blank label."""
        a = group_avail([group_rate(2536321, title='Group(1~6) Harf Day')],
                         [group_price(2536321, 40000)])
        r = bokun_price.rows(a, GROUP_CATS)
        self.assertEqual(bokun_price.format_full(r, 'ja'), ['Group(1~6) Harf Day: ¥40,000'])

    def test_group_row_without_a_rate_title_falls_back_to_group_and_tier(self):
        """Defensive fallback for incomplete data (e.g. a hand-written
        sample-tour row) — must not crash, and must not render a blank
        label."""
        r = [{'category': None, 'min': 1, 'max': 6, 'amount': 40000,
              'currency': 'JPY', 'per_booking': True}]
        self.assertEqual(bokun_price.format_full(r, 'en'), ['Group, 1–6 guests: ¥40,000'])


class TestMergeDuplicateTiers(unittest.TestCase):
    """Real Bokun availability often lists one row per exact participant
    count at the same price, rather than one ready-made range (seen on
    Ikebana: 3, 4, 5 and 6 guests each as a separate ¥21,000 row). Task 14
    requires these to collapse into one row per distinct price, not repeat
    the same amount several times."""

    def test_identical_amount_single_count_tiers_collapse_into_one_range(self):
        r = bokun_price.rows(avail([
            unit(1, 21000, 5, 5), unit(1, 21000, 4, 4), unit(1, 21000, 6, 6),
            unit(1, 21000, 3, 3), unit(1, 44000, 1, 2),
        ]), CATS)
        self.assertEqual(bokun_price.format_full(r, 'en'),
                          ['Adult, 1–2 guests: ¥44,000', 'Adult, 3–6 guests: ¥21,000'])

    def test_merge_never_crosses_different_amounts(self):
        r = bokun_price.rows(avail([unit(1, 12000, 3, 3), unit(1, 12000, 4, 4),
                                    unit(1, 29000, 1, 2)]), CATS)
        self.assertEqual(bokun_price.format_full(r, 'en'),
                          ['Adult, 1–2 guests: ¥29,000', 'Adult, 3–4 guests: ¥12,000'])


class TestHasPriceBreakdown(unittest.TestCase):
    def test_no_rows_has_no_breakdown(self):
        self.assertFalse(bokun_price.has_price_breakdown([]))

    def test_a_single_row_has_no_breakdown(self):
        r = bokun_price.rows(avail([unit(1, 23000)]), CATS)
        self.assertFalse(bokun_price.has_price_breakdown(r))

    def test_several_rows_all_the_same_amount_have_no_breakdown(self):
        """If every tier costs the same, the table would only restate the
        headline 'from' price — render nothing (task 14, rule 5)."""
        r = bokun_price.rows(avail([unit(1, 21000, 1, 6), unit(1, 21000, 7, 10)]), CATS)
        self.assertFalse(bokun_price.has_price_breakdown(r))

    def test_two_different_amounts_have_a_breakdown(self):
        r = bokun_price.rows(avail([unit(1, 44000, 1, 2), unit(1, 21000, 3, 6)]), CATS)
        self.assertTrue(bokun_price.has_price_breakdown(r))


if __name__ == '__main__':
    unittest.main()
