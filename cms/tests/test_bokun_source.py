import json, os, unittest
from cms import bokun_source, tours_config

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
IKEBANA, CANDLE, ZEN, SWORD = 1273232, 1273235, 1273194, 1275339
OTA_IDS = [1272734, 1272756, 1272817, 1272825, 1272835, 1272849, 1273963]


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


class FakeClient:
    """Serves the recorded fixtures and records the paths asked for."""

    def __init__(self, product_list=None):
        self.paths, self._list = [], product_list

    def get(self, path):
        self.paths.append(path)
        if path.startswith('/product-list.json/list'):
            return self._list if self._list is not None else []
        if '/availabilities' in path:
            pid = int(path.split('/')[2])
            return load(f'availability-{pid}.json')
        if path.startswith('/activity.json/'):
            pid = int(path.split('/')[2].split('?')[0])
            lang = 'ja' if 'lang=ja' in path else 'EN'
            return load(f'activity-{pid}-{lang}.json')
        raise AssertionError('unexpected path ' + path)

    def post(self, path, body):
        raise AssertionError('no POST expected')


CFG = {
    'productListName': 'Website',
    'allowlist': [IKEBANA, CANDLE, ZEN, SWORD],
    'otaDenylist': OTA_IDS,
    'corrections': {'templ e grounds': 'temple grounds', 'wa l ked': 'walked',
                    'passag e through': 'passage through',
                    'templ e cuisine': 'temple cuisine'},
    'tours': {
        str(IKEBANA): {'slug': 'ikebana-ichigo-ichie', 'number': '01', 'area': 'Kamakura',
                       'length': 'Half-day', 'themes': ['Arts & Craft'], 'jaReviewed': False,
                       'widgets': {'en': 'CH/experience-calendar/1273232'}},
        str(CANDLE): {'slug': 'candle-making', 'number': '02', 'area': 'Kamakura',
                      'length': 'Half-day', 'themes': ['Arts & Craft'], 'jaReviewed': False,
                      'widgets': {}},
        str(ZEN): {'slug': 'zen-journey', 'number': '03', 'area': 'Kamakura',
                   'length': 'Half-day', 'themes': ['Walking'], 'jaReviewed': False,
                   'widgets': {}},
        str(SWORD): {'slug': 'swordsmithing', 'number': '04', 'area': 'Kamakura',
                     'length': 'Half-day', 'themes': ['Arts & Craft'], 'jaReviewed': False,
                     'widgets': {}},
    },
}


class TestCatalogue(unittest.TestCase):
    def test_prefers_the_named_product_list(self):
        c = FakeClient(product_list=[{'id': 77, 'title': 'Website',
                                      'items': [{'activityId': IKEBANA}]}])
        self.assertEqual(bokun_source.catalogue(c, CFG), [IKEBANA])

    def test_falls_back_to_the_allowlist_when_no_list_exists(self):
        self.assertEqual(bokun_source.catalogue(FakeClient(product_list=[]), CFG),
                         [IKEBANA, CANDLE, ZEN, SWORD])

    def test_ignores_product_lists_with_a_different_name(self):
        c = FakeClient(product_list=[{'id': 1, 'title': 'OTA', 'items': [{'activityId': 999}]}])
        self.assertEqual(bokun_source.catalogue(c, CFG), [IKEBANA, CANDLE, ZEN, SWORD])

    def test_denylisted_id_from_the_product_list_is_rejected(self):
        ota_id = OTA_IDS[0]
        c = FakeClient(product_list=[{'id': 77, 'title': 'Website',
                                      'items': [{'activityId': IKEBANA},
                                                {'activityId': ota_id}]}])
        with self.assertRaises(tours_config.ConfigError) as ctx:
            bokun_source.catalogue(c, CFG)
        self.assertIn(str(ota_id), str(ctx.exception))

    def test_denylisted_id_from_the_allowlist_is_rejected(self):
        ota_id = OTA_IDS[0]
        cfg = dict(CFG, productListName='', allowlist=[IKEBANA, ota_id])
        with self.assertRaises(tours_config.ConfigError) as ctx:
            bokun_source.catalogue(FakeClient(product_list=[]), cfg)
        self.assertIn(str(ota_id), str(ctx.exception))


class TestRecords(unittest.TestCase):
    def setUp(self):
        self.records, self.warnings = bokun_source.fetch_records(FakeClient(), CFG)
        self.by_slug = {r['id']: r for r in self.records}

    def test_one_record_per_catalogue_product(self):
        self.assertEqual(sorted(self.by_slug),
                         ['candle-making', 'ikebana-ichigo-ichie', 'swordsmithing', 'zen-journey'])

    def test_slug_and_number_come_from_config_not_bokun(self):
        r = self.by_slug['ikebana-ichigo-ichie']
        self.assertEqual(r['id'], 'ikebana-ichigo-ichie')
        self.assertEqual(r['number'], '01')
        self.assertEqual(r['bokunId'], IKEBANA)

    def test_title_is_cleaned_of_entities(self):
        for r in self.records:
            self.assertNotIn('&#', r['titleEn'])
            self.assertNotIn('&nbsp;', r['ledeEn'])

    def test_corrections_are_applied_to_the_lede(self):
        lede = self.by_slug['zen-journey']['ledeEn'] + ' ' + self.by_slug['zen-journey']['subEn']
        self.assertNotIn('templ e', lede)
        self.assertNotIn('wa l ked', lede)

    def test_ikebana_from_price_is_the_lowest_adult_tier(self):
        self.assertEqual(self.by_slug['ikebana-ichigo-ichie']['priceEn'],
                         'from ¥21,000 per adult')

    def test_candle_from_price_is_the_lowest_adult_tier(self):
        self.assertEqual(self.by_slug['candle-making']['priceEn'], 'from ¥12,000 per adult')

    def test_unpriced_products_have_no_price_and_no_price_rows(self):
        for slug in ('zen-journey', 'swordsmithing'):
            self.assertEqual(self.by_slug[slug]['priceEn'], '')
            self.assertEqual(self.by_slug[slug]['priceRows'], [])

    def test_japanese_mirrors_english_until_jaReviewed(self):
        r = self.by_slug['ikebana-ichigo-ichie']
        self.assertEqual(r['titleJa'], r['titleEn'])
        self.assertEqual(r['ledeJa'], r['ledeEn'])

    def test_duration_text_does_localise_even_when_unreviewed(self):
        r = self.by_slug['ikebana-ichigo-ichie']
        self.assertNotEqual(r['hoursJa'], r['hoursEn'])

    def test_cover_comes_from_the_first_photo(self):
        self.assertTrue(self.by_slug['ikebana-ichigo-ichie']['cover']['url'].startswith('http'))

    def test_ikebana_inclusions_are_extracted_from_the_description(self):
        items = self.by_slug['ikebana-ichigo-ichie']['includedEn'].split('\n')
        self.assertIn('Tour insurance', items)
        self.assertTrue(any('flower materials' in i for i in items))
        self.assertFalse(any('PDF' == i.strip() for i in items))

    def test_inclusions_do_not_leak_into_the_lede(self):
        self.assertNotIn('What is Included',
                         self.by_slug['ikebana-ichigo-ichie']['ledeEn'])
        self.assertNotIn('Tour insurance',
                         self.by_slug['ikebana-ichigo-ichie']['ledeEn'])

    def test_products_without_an_inclusions_list_have_no_chips(self):
        for slug in ('candle-making', 'zen-journey', 'swordsmithing'):
            self.assertEqual(self.by_slug[slug]['includedEn'], '', slug)

    def test_fields_bokun_has_no_data_for_stay_empty(self):
        for r in self.records:
            for f in ('notIncludedEn', 'notAllowedEn', 'notSuitableEn'):
                self.assertEqual(r[f], '', f)

    def test_route_comes_from_agenda_items_and_is_empty_where_there_are_none(self):
        self.assertTrue(len(self.by_slug['ikebana-ichigo-ichie']['route']) >= 3)
        self.assertEqual(self.by_slug['candle-making']['route'], [])
        self.assertEqual(self.by_slug['swordsmithing']['route'], [])

    def test_widgets_carry_through_from_config(self):
        self.assertEqual(self.by_slug['ikebana-ichigo-ichie']['widgets'],
                         {'en': 'CH/experience-calendar/1273232'})

    def test_no_ota_product_can_appear(self):
        for r in self.records:
            self.assertNotIn(r['bokunId'],
                             [1272734, 1272756, 1272817, 1272825, 1272835, 1272849, 1273963])

    def test_uncovered_damage_surfaces_as_a_warning(self):
        records, warnings = bokun_source.fetch_records(
            FakeClient(), dict(CFG, corrections={}))
        self.assertTrue(any('spacing damage' in w for w in warnings))

    def test_a_correction_only_used_in_an_agenda_item_is_not_reported_as_prunable(self):
        # 'templ e cuisine' only occurs in zen-journey's agendaItems[1].body
        # (a route step), not in any title/excerpt/description. It must still
        # count as "used" so the warning never tells an editor it is safe to
        # remove — removing it would let the damage reach the live route text.
        for w in self.warnings:
            self.assertNotIn('templ e cuisine', w)


class TestJaReviewed(unittest.TestCase):
    def test_reviewed_fields_are_sourced_from_the_ja_response(self):
        activity = load(f'activity-{IKEBANA}-EN.json')
        # Bokun's real ja fixtures happen to hold English text (the client's
        # actual data-entry state), so a content diff can't prove provenance.
        # Build a distinguishable synthetic ja response instead, and assert
        # on where the text came from rather than what language it's in.
        activity_ja = dict(activity, title='JA-SENTINEL title',
                            excerpt='JA-SENTINEL excerpt',
                            description='JA-SENTINEL description')
        entry = dict(CFG['tours'][str(IKEBANA)], jaReviewed=True)
        rec, warnings, raw_texts = bokun_source.to_record(
            activity, activity_ja, [], entry, {})

        self.assertIn('JA-SENTINEL title', rec['titleJa'])
        self.assertIn('JA-SENTINEL excerpt', rec['subJa'])
        self.assertIn('JA-SENTINEL description', rec['ledeJa'])
        self.assertNotEqual(rec['titleJa'], rec['titleEn'])
        self.assertNotEqual(rec['subJa'], rec['subEn'])
        self.assertNotEqual(rec['ledeJa'], rec['ledeEn'])

        # Bokun has no data for these at all, reviewed or not.
        for f in ('notIncludedEn', 'notIncludedJa', 'notAllowedEn', 'notAllowedJa',
                  'notSuitableEn', 'notSuitableJa'):
            self.assertEqual(rec[f], '', f)


if __name__ == '__main__':
    unittest.main()
