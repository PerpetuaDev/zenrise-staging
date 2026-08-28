# cms/tests/test_party_range.py
"""The traveller count beside the price.

It used to be the literal string '1-6 travelers' on every tour, which was
wrong for most of the catalogue: ikebana is priced for 1-2 only and
candle-making for at most 4, so the site invited bookings Bokun cannot price.
It is now read from the rate tiers.
"""
import importlib.util, os, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_tours', os.path.join(ROOT, 'cms', 'build-tours.py'))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)


def rows(*pairs):
    return [{'category': 'Adults', 'min': lo, 'max': hi,
             'amount': 1000, 'currency': 'JPY'} for lo, hi in pairs]


class TestRange(unittest.TestCase):
    def test_single_tier_spans_its_own_min_and_max(self):
        self.assertEqual(bt.party_range(rows((1, 2))), (1, 2))

    def test_several_tiers_span_the_widest_pair(self):
        # candle-making's real shape: 1-2, 3-3, 4-4 -> 1 through 4.
        self.assertEqual(bt.party_range(rows((4, 4), (3, 3), (1, 2))), (1, 4))

    def test_no_rows_means_no_range(self):
        self.assertIsNone(bt.party_range([]))

    def test_rows_without_bounds_are_ignored(self):
        self.assertIsNone(bt.party_range([{'category': 'Adults', 'amount': 1}]))


class TestEnglishLabel(unittest.TestCase):
    def test_a_span_reads_as_a_range(self):
        self.assertEqual(bt.party_label(rows((1, 4)), 'en'), '1–4 travelers')

    def test_a_fixed_size_does_not_repeat_itself(self):
        self.assertEqual(bt.party_label(rows((4, 4)), 'en'), '4 travelers')

    def test_a_solo_tour_is_singular(self):
        self.assertEqual(bt.party_label(rows((1, 1)), 'en'), '1 traveler')

    def test_no_rows_gives_no_label(self):
        self.assertEqual(bt.party_label([], 'en'), '')


class TestJapaneseLabel(unittest.TestCase):
    def test_a_span_reads_as_a_range(self):
        self.assertEqual(bt.party_label(rows((1, 4)), 'ja'), '1〜4名')

    def test_a_fixed_size_does_not_repeat_itself(self):
        self.assertEqual(bt.party_label(rows((4, 4)), 'ja'), '4名')

    def test_no_rows_gives_no_label(self):
        self.assertEqual(bt.party_label([], 'ja'), '')


class TestEyebrow(unittest.TestCase):
    """The eyebrow joins price and party size; neither half may leave a
    dangling separator when it is missing."""

    def model(self, price_rows, price_en='from ¥44,000 per adult',
              price_ja='¥44,000〜（大人おひとり）'):
        from cms.tests.test_tours_render import record
        return bt.tour_model(record(priceRows=price_rows, priceEn=price_en,
                                    priceJa=price_ja))

    def test_real_ikebana_no_longer_claims_six(self):
        en, ja = bt.base_dict(self.model(rows((1, 2))))
        K = 'tours_ikebana-ichigo-ichie_cta_eyebrow'
        self.assertEqual(en[K], 'from ¥44,000 per adult ・ 1–2 travelers')
        self.assertEqual(ja[K], '¥44,000〜（大人おひとり） ・ 1〜2名')

    def test_an_unpriced_tour_has_no_dangling_separator(self):
        en, ja = bt.base_dict(self.model([], price_en='', price_ja=''))
        K = 'tours_ikebana-ichigo-ichie_cta_eyebrow'
        self.assertEqual(en[K], '')
        self.assertEqual(ja[K], '')

    def test_the_detail_slot_matches_the_card(self):
        m = self.model(rows((1, 2)))
        en, _ = bt.base_dict(m)
        self.assertEqual(bt.common_slots(m)['CTA_EYEBROW_EN'],
                         en['tours_ikebana-ichigo-ichie_cta_eyebrow'])


class TestNoHardcodedRange(unittest.TestCase):
    def test_the_literal_string_is_gone_from_the_builder(self):
        src = open(os.path.join(ROOT, 'cms', 'build-tours.py'), encoding='utf-8').read()
        self.assertNotIn('1–6 travelers', src)
        self.assertNotIn('1〜6名', src)


if __name__ == '__main__':
    unittest.main()
