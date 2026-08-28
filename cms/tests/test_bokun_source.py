import json, os, tempfile, unittest
from cms import bokun_price, bokun_source, bokun_text, tours_config, tours_slug

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
IKEBANA, CANDLE, ZEN, SWORD = 1273232, 1273235, 1273194, 1275339
OTA_IDS = [1272734, 1272756, 1272817, 1272825, 1272835, 1272849, 1273963]


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


class FakeClient:
    """Serves the recorded fixtures and records the paths asked for.

    Product lists are served the way the real API actually shapes them
    (verified 2026-08-26, task-3-4 brief): `/product-list.json/list` returns
    SUMMARIES only (no membership), and a matching list's membership comes
    from a second call to `/product-list.json/<id>`, whose `items` are
    `{'activity': {'id': ..., 'title': ...}, 'productCategory': ...}`.

    `overrides` lets a test replace or delete arbitrary keys on an
    already-recorded activity fixture (e.g. to flip marketplaceVisibilityType,
    or to blank out photos/description) without re-recording it -- keyed
    '<pid>-<lang>', value either a dict of key overrides or the sentinel
    DELETE_KEYS to remove keys entirely.
    """

    def __init__(self, product_list=None, product_list_items=None, overrides=None,
                 baseline=True):
        self.paths = []
        self._list = product_list
        self._items = product_list_items or {}
        self._overrides = overrides or {}
        self._baseline = baseline

    def get(self, path):
        self.paths.append(path)
        if path.startswith('/product-list.json/list'):
            return self._list if self._list is not None else []
        if path.startswith('/product-list.json/'):
            list_id = int(path.split('/')[2])
            items = self._items.get(list_id, [])
            return {'id': list_id, 'items': items}
        if '/availabilities' in path:
            pid = int(path.split('/')[2])
            return load(f'availability-{pid}.json')
        if path.startswith('/activity.json/'):
            pid = int(path.split('/')[2].split('?')[0])
            lang = 'ja' if 'lang=ja' in path else 'EN'
            data = load(f'activity-{pid}-{lang}.json')
            if self._baseline:
                data = dict(data, **BASELINE.get(lang, {}))
            ov = self._overrides.get(f'{pid}-{lang}')
            if ov:
                data = dict(data)
                for k, v in ov.items():
                    if v is DELETE:
                        data.pop(k, None)
                    else:
                        data[k] = v
            return data
        raise AssertionError('unexpected path ' + path)

    def post(self, path, body):
        raise AssertionError('no POST expected')


DELETE = object()

# The recorded fixtures are from 2026-08-25, before the client's bilingual
# work: no product carries an `en` version and every Japanese slot holds
# English, so under the publish gates every one of them would be held back.
# FakeClient therefore serves them lifted through the LANGUAGE gates, letting
# each test target one gate at a time; a test exercising a language gate
# overrides these back (see test_publish_gates) or passes baseline=False.
BASELINE = {
    'EN': {'languages': ['en', 'JA_JP']},
    'ja': {'description': '<p>鎌倉の禅寺をめぐる、静かな半日の旅です。</p>'
                          '<p>坐禅を組み、抹茶と和菓子をお召し上がりいただきます。</p>'},
}


def list_item(activity_id):
    """One /product-list.json/<id> membership row for `activity_id`."""
    return {'activity': {'id': activity_id, 'title': 'x'}, 'productCategory': 'x'}


CFG = {
    'productListName': 'Website',
    'allowlist': [IKEBANA, CANDLE, ZEN, SWORD],
    'otaDenylist': OTA_IDS,
    'corrections': {'templ e grounds': 'temple grounds', 'wa l ked': 'walked',
                    'passag e through': 'passage through',
                    'templ e cuisine': 'temple cuisine'},
    'tours': {
        str(IKEBANA): {'slug': 'ikebana-ichigo-ichie', 'number': '01', 'area': 'Kamakura',
                       'themes': ['arts'], 'jaReviewed': False,
                       'widgets': {'en': 'CH/experience-calendar/1273232'}},
        str(CANDLE): {'slug': 'candle-making', 'number': '02', 'area': 'Kamakura',
                      'themes': ['arts'], 'jaReviewed': False,
                      'widgets': {}},
        str(ZEN): {'slug': 'zen-journey', 'number': '03', 'area': 'Kamakura',
                   'themes': ['walking'], 'jaReviewed': False,
                   'widgets': {}},
        str(SWORD): {'slug': 'swordsmithing', 'number': '04', 'area': 'Kamakura',
                     'themes': ['arts'], 'jaReviewed': False,
                     'widgets': {}},
    },
}


class TestCatalogue(unittest.TestCase):
    def test_prefers_the_named_product_list(self):
        c = FakeClient(product_list=[{'id': 77, 'title': 'Website'}],
                       product_list_items={77: [list_item(IKEBANA)]})
        self.assertEqual(bokun_source.catalogue(c, CFG), [IKEBANA])

    def test_list_membership_requires_the_per_list_detail_call(self):
        # /product-list.json/list returns summaries only -- no 'items' key at
        # all -- so catalogue() must not (mis)read membership off it directly.
        c = FakeClient(product_list=[{'id': 77, 'title': 'Website'}],
                       product_list_items={77: [list_item(IKEBANA)]})
        bokun_source.catalogue(c, CFG)
        self.assertIn('/product-list.json/77', c.paths)

    def test_falls_back_to_the_allowlist_when_no_list_exists(self):
        self.assertEqual(bokun_source.catalogue(FakeClient(product_list=[]), CFG),
                         [IKEBANA, CANDLE, ZEN, SWORD])

    def test_fallback_is_warned_about(self):
        warnings = []
        bokun_source.catalogue(FakeClient(product_list=[]), CFG, warnings=warnings)
        self.assertTrue(any('falling back' in w for w in warnings), warnings)

    def test_a_present_but_empty_list_publishes_nothing_not_a_fallback(self):
        c = FakeClient(product_list=[{'id': 77, 'title': 'Website'}],
                       product_list_items={77: []})
        warnings = []
        self.assertEqual(bokun_source.catalogue(c, CFG, warnings=warnings), [])
        self.assertFalse(any('falling back' in w for w in warnings), warnings)

    def test_ignores_product_lists_with_a_different_name(self):
        c = FakeClient(product_list=[{'id': 1, 'title': 'OTA'}],
                       product_list_items={1: [list_item(999)]})
        self.assertEqual(bokun_source.catalogue(c, CFG), [IKEBANA, CANDLE, ZEN, SWORD])

    def test_denylisted_id_from_the_product_list_is_rejected(self):
        ota_id = OTA_IDS[0]
        c = FakeClient(product_list=[{'id': 77, 'title': 'Website'}],
                       product_list_items={77: [list_item(IKEBANA), list_item(ota_id)]})
        with self.assertRaises(tours_config.ConfigError) as ctx:
            bokun_source.catalogue(c, CFG)
        self.assertIn(str(ota_id), str(ctx.exception))

    def test_tier_products_the_list_omits_are_named_in_the_log(self):
        # a tour vanishing silently is the failure this logging prevents
        c = FakeClient(product_list=[{'id': 77, 'title': 'Website'}],
                       product_list_items={77: [list_item(IKEBANA)]})
        warnings = []
        bokun_source.catalogue(c, CFG, warnings=warnings)
        held = [w for w in warnings if 'held back' in w]
        self.assertTrue(any(str(SWORD) in w for w in held), warnings)
        self.assertFalse(any(str(IKEBANA) in w for w in held), warnings)

    def test_an_omitted_product_is_a_warning_not_a_note(self):
        c = FakeClient(product_list=[{'id': 77, 'title': 'Website'}],
                       product_list_items={77: [list_item(IKEBANA)]})
        warnings = []
        bokun_source.catalogue(c, CFG, warnings=warnings)
        for w in warnings:
            if 'held back' in w:
                self.assertNotIsInstance(w, bokun_source.Note, w)
            if 'member(s)' in w:
                self.assertIsInstance(w, bokun_source.Note, w)

    def test_no_ota_product_is_ever_named_as_merely_held_back(self):
        # an OTA id must raise, never be reported as a publishable tour the
        # list happens to omit
        c = FakeClient(product_list=[{'id': 77, 'title': 'Website'}],
                       product_list_items={77: [list_item(IKEBANA)]})
        warnings = []
        bokun_source.catalogue(c, CFG, warnings=warnings)
        for ota in OTA_IDS:
            self.assertFalse(any(str(ota) in w for w in warnings), ota)

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
        # Swordsmithing is absent by design: unpriced and with no availability,
        # it cannot be booked, so it is held back rather than published.
        self.assertEqual(sorted(self.by_slug),
                         ['candle-making', 'ikebana-ichigo-ichie', 'zen-journey'])

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

    def test_every_record_is_priced(self):
        # Unpriced products are held back now, so a record without a price
        # would mean a gate had leaked.
        for slug, rec in self.by_slug.items():
            self.assertTrue(rec['priceEn'], slug)
            self.assertTrue(rec['priceRows'], slug)

    def test_zen_journey_reads_as_both_lengths_from_its_real_rates(self):
        self.assertEqual(self.by_slug['zen-journey']['length'], 'Full / Half-day')

    def test_rates_beat_the_activity_duration(self):
        # Zen Journey's durationText is 4 hours, which alone derives Half-day;
        # it sells a full day too, and what is bookable wins.
        self.assertEqual(self.by_slug['zen-journey']['hoursEn'], '4 hours')
        self.assertNotEqual(self.by_slug['zen-journey']['length'], 'Half-day')

    def test_tours_whose_rates_say_nothing_keep_the_duration_length(self):
        for slug in ('candle-making', 'ikebana-ichigo-ichie'):
            self.assertEqual(self.by_slug[slug]['length'], 'Half-day', slug)

    def test_zen_journey_is_group_priced_from_its_cheaper_rate(self):
        """The Zen Journey is priced per booking (Half Day ¥40,000, Full Day
        ¥70,000), not per person, so it must show the cheaper group price
        rather than coming back unpriced. See task 13."""
        r = self.by_slug['zen-journey']
        self.assertEqual(r['priceEn'], 'from ¥40,000 per group')
        self.assertEqual(r['priceJa'], '¥40,000〜（1グループ）')
        self.assertTrue(r['priceRows'])
        self.assertTrue(all(row.get('per_booking') for row in r['priceRows']))

    def test_japanese_comes_from_the_ja_payload(self):
        # FakeClient's BASELINE puts real Japanese in the description slot, so
        # the lede must come from there rather than mirroring English.
        r = self.by_slug['ikebana-ichigo-ichie']
        self.assertNotEqual(r['ledeJa'], r['ledeEn'])

    def test_duration_text_localises(self):
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
        for slug in ('candle-making', 'zen-journey'):
            self.assertEqual(self.by_slug[slug]['includedEn'], '', slug)

    def test_fields_bokun_has_no_data_for_stay_empty(self):
        # The fixtures predate the structured prose fields (task 17): none of
        # excluded/requirements/attention exist on these recorded activities,
        # so their record fields stay empty exactly as before.
        for r in self.records:
            for f in ('notIncludedEn', 'bringEn', 'knowEn'):
                self.assertEqual(r[f], '', f)

    def test_fixtures_predate_the_enum_chip_fields_too(self):
        # The recorded fixtures also predate `inclusions`/
        # `knowBeforeYouGoItems` (task 18): neither exists on these
        # activities, so the enum chip record fields stay empty.
        for r in self.records:
            for f in ('includedChipsEn', 'includedChipsJa', 'knowChipsEn', 'knowChipsJa'):
                self.assertEqual(r[f], '', f)

    def test_route_comes_from_agenda_items_and_is_empty_where_there_are_none(self):
        self.assertTrue(len(self.by_slug['ikebana-ichigo-ichie']['route']) >= 3)
        self.assertEqual(self.by_slug['candle-making']['route'], [])

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


class TestLengthFromRates(unittest.TestCase):
    """Bokun has no per-rate duration, so rate titles are the only signal."""

    def rows(self, *titles, ja=None):
        return [{'rate_title': t, 'rate_title_ja': (ja or t)} for t in titles]

    def test_both_options_present(self):
        self.assertEqual(
            bokun_source._length_from_rates(
                self.rows('Group(1~6) Half Day', 'Group(1~6) Full Day')),
            'Full / Half-day')

    def test_full_day_only(self):
        self.assertEqual(
            bokun_source._length_from_rates(self.rows('Full Day Private')),
            'Full-day')

    def test_half_day_only(self):
        self.assertEqual(
            bokun_source._length_from_rates(self.rows('Half-day Group')),
            'Half-day')

    def test_rates_that_say_nothing_defer(self):
        # the real shape for three of the four tours
        self.assertEqual(
            bokun_source._length_from_rates(self.rows('Standard Private Group ')), '')
        self.assertEqual(bokun_source._length_from_rates([]), '')

    def test_tolerates_the_clients_harf_typo(self):
        # it reached the live account once already
        self.assertEqual(
            bokun_source._length_from_rates(self.rows('Group Harf Day', 'Group Full Day')),
            'Full / Half-day')

    def test_reads_japanese_rate_titles(self):
        # today the ja titles mirror English; this keeps working when they stop
        self.assertEqual(
            bokun_source._length_from_rates(
                [{'rate_title': 'A', 'rate_title_ja': '\u534a\u65e5\u30d7\u30e9\u30f3'},
                 {'rate_title': 'B', 'rate_title_ja': '\u4e00\u65e5\u30d7\u30e9\u30f3'}]),
            'Full / Half-day')

    def test_a_half_day_title_is_not_read_as_a_full_day(self):
        # '\u534a\u65e5' shares a character with '\u4e00\u65e5' and '1\u65e5'
        self.assertEqual(
            bokun_source._length_from_rates(
                [{'rate_title': '', 'rate_title_ja': '\u534a\u65e5'}]),
            'Half-day')


class TestAmbiguousRateNaming(unittest.TestCase):
    """The one soft spot in deriving length from rate names."""

    def warn(self, *titles):
        rows = [{'rate_title': t, 'rate_title_ja': t, 'amount': 1, 'min': 1,
                 'max': 6, 'per_booking': True, 'category': None,
                 'category_ja': None, 'currency': 'JPY'} for t in titles]
        distinct = {(r.get('rate_title') or '').strip()
                    for r in rows if (r.get('rate_title') or '').strip()}
        return len(distinct) > 1 and not bokun_source._length_from_rates(rows)

    def test_two_opaque_rate_names_are_flagged(self):
        self.assertTrue(self.warn('Short course', 'Long course'))

    def test_group_size_tiers_sharing_one_name_are_not_flagged(self):
        # candle-making and ikebana: many rows, one rate name, no ambiguity
        self.assertFalse(self.warn('Standard Private Group ',
                                   'Standard Private Group '))

    def test_a_single_rate_is_not_flagged(self):
        self.assertFalse(self.warn('Standard Private Group '))

    def test_correctly_named_rates_are_not_flagged(self):
        self.assertFalse(self.warn('Group(1~6) Half Day', 'Group(1~6) Full Day'))


class TestChipFields(unittest.TestCase):
    """The four fixed Bokun fields that feed the four PROSE groups (task 17,
    reclassified as prose rather than chips in task 18):
    included/excluded/requirements/attention. The recorded fixtures predate
    these fields entirely (they simply don't exist on the recorded
    activities), so every shape below is built synthetically, matching what
    was verified live on product 1273194 -- see the task-17 brief."""

    def _activity(self, pid, **fields):
        return dict(load(f'activity-{pid}-EN.json'), **fields)

    def test_li_items_are_extracted_cleaned_and_counted(self):
        activity = self._activity(
            ZEN,
            included=('<div>\r\n <p style="font-size:14px"><strong>What\'s '
                       'included in the tour</strong></p>\r\n '
                       '<ul><li style="x">Guide</li><li style="x">Entrance fees'
                       '</li><li style="x">Matcha &amp; wagashi</li></ul></div>'))
        entry = CFG['tours'][str(ZEN)]
        rec, warnings, raw_texts = bokun_source.to_record(
            activity, activity, [], [], entry, {})
        self.assertEqual(rec['includedEn'].split('\n'),
                          ['Guide', 'Entrance fees', 'Matcha & wagashi'])

    def test_corrections_apply_inside_chip_items_and_are_marked_used(self):
        activity = self._activity(
            ZEN, included='<ul><li>A quiet passag e through the garden</li></ul>')
        entry = CFG['tours'][str(ZEN)]
        corr = {'passag e through': 'passage through'}
        rec, warnings, raw_texts = bokun_source.to_record(
            activity, activity, [], [], entry, corr)
        self.assertEqual(rec['includedEn'], 'A quiet passage through the garden')
        self.assertNotIn('passag e through',
                          bokun_text.unused_corrections(raw_texts, corr))

    def test_all_four_fields_map_to_their_own_group(self):
        activity = self._activity(
            ZEN,
            included='<ul><li>A</li><li>B</li></ul>',
            excluded='<ul><li>C</li></ul>',
            requirements='<ul><li>D</li></ul>',
            attention='<ul><li>E</li><li>F</li><li>G</li></ul>')
        entry = CFG['tours'][str(ZEN)]
        rec, *_ = bokun_source.to_record(activity, activity, [], [], entry, {})
        self.assertEqual(rec['includedEn'], 'A\nB')
        self.assertEqual(rec['notIncludedEn'], 'C')
        self.assertEqual(rec['bringEn'], 'D')
        self.assertEqual(rec['knowEn'], 'E\nF\nG')

    def test_ikebana_falls_back_to_description_parsing_for_included(self):
        # Ikebana's real shape: the included field holds one prose sentence
        # with no <li>, while its description still carries a 6-item
        # "What is Included:" list. Chips must come from the description,
        # not go empty. See regression anchor in the task-17 brief.
        activity = self._activity(
            IKEBANA,
            included='<p>Tea and seasonal wagashi are included in every session.</p>')
        entry = CFG['tours'][str(IKEBANA)]
        rec, *_ = bokun_source.to_record(activity, activity, [], [], entry, {})
        items = rec['includedEn'].split('\n')
        self.assertEqual(len(items), 6)
        self.assertIn('Tour insurance', items)

    def test_field_with_no_list_and_no_description_fallback_uses_its_own_plain_text(self):
        # excluded/requirements/attention have no description-parsing
        # fallback -- only included does -- so a prose field with no <li>
        # becomes a single chip made of its own plain text.
        activity = self._activity(
            ZEN, excluded='<p>Transport to and from your accommodation.</p>')
        entry = CFG['tours'][str(ZEN)]
        rec, *_ = bokun_source.to_record(activity, activity, [], [], entry, {})
        self.assertEqual(rec['notIncludedEn'], 'Transport to and from your accommodation.')

    def test_a_field_with_no_content_at_all_stays_empty(self):
        # Candle-making and Swordsmithing: all four fields empty, so no
        # group is populated and chips_section() must render nothing.
        activity = self._activity(CANDLE, requirements='')
        entry = CFG['tours'][str(CANDLE)]
        rec, *_ = bokun_source.to_record(activity, activity, [], [], entry, {})
        self.assertEqual(rec['bringEn'], '')

    def test_japanese_chip_content_comes_from_the_ja_payload_when_reviewed(self):
        activity = self._activity(ZEN, included='<ul><li>Guide (EN)</li></ul>')
        activity_ja = self._activity(ZEN, included='<ul><li>ガイド</li></ul>')
        entry = dict(CFG['tours'][str(ZEN)], jaReviewed=True)
        rec, *_ = bokun_source.to_record(activity, activity_ja, [], [], entry, {})
        self.assertEqual(rec['includedEn'], 'Guide (EN)')
        self.assertEqual(rec['includedJa'], 'ガイド')

    def test_japanese_chip_content_is_used_as_written(self):
        # Japanese is the authored original, so it is shown as written; the
        # publish gates already refuse a tour whose Japanese slot is English.
        activity = self._activity(ZEN, included='<ul><li>Guide (EN)</li></ul>')
        activity_ja = self._activity(ZEN, included='<ul><li>ガイド</li></ul>')
        entry = dict(CFG['tours'][str(ZEN)])
        rec, *_ = bokun_source.to_record(activity, activity_ja, [], [], entry, {})
        self.assertEqual(rec['includedJa'], 'ガイド')
        self.assertNotEqual(rec['includedJa'], rec['includedEn'])

    def test_japanese_falls_back_to_english_when_the_ja_field_is_empty_even_if_reviewed(self):
        activity = self._activity(ZEN, included='<ul><li>Guide (EN)</li></ul>')
        activity_ja = self._activity(ZEN, included='')
        entry = dict(CFG['tours'][str(ZEN)], jaReviewed=True)
        rec, *_ = bokun_source.to_record(activity, activity_ja, [], [], entry, {})
        self.assertEqual(rec['includedJa'], 'Guide (EN)')


class TestEnumChipFields(unittest.TestCase):
    """Task 18: `inclusions` and `knowBeforeYouGoItems` are closed Bokun enum
    vocabularies (lists of SCREAMING_SNAKE constants), mapped to real chip
    labels via cms/bokun_labels.py. The recorded fixtures predate both
    fields (verified empty live for all four real tours in the fixture
    window), so every shape here is built synthetically, matching what was
    verified live on product 1273194 -- see the task-18 brief."""

    def _activity(self, pid, **fields):
        return dict(load(f'activity-{pid}-EN.json'), **fields)

    def test_zen_journey_shape_maps_five_inclusions_to_five_chips(self):
        # Verified live on 1273194: BUS_FARE, PARKING_FEES, FOOD_AND_DRINKS,
        # ENTRY_OR_ADMISSION_FEE, GOODS_AND_SERVICES_TAX.
        activity = self._activity(
            ZEN, inclusions=['BUS_FARE', 'PARKING_FEES', 'FOOD_AND_DRINKS',
                              'ENTRY_OR_ADMISSION_FEE', 'GOODS_AND_SERVICES_TAX'])
        entry = CFG['tours'][str(ZEN)]
        rec, warnings, _ = bokun_source.to_record(activity, activity, [], [], entry, {})
        self.assertEqual(rec['includedChipsEn'].split('\n'),
                         ['Bus fare', 'Parking fees', 'Food & drinks',
                          'Entry & admission fees', 'Tax'])
        self.assertEqual(rec['includedChipsJa'].split('\n'),
                         ['バス運賃', '駐車料金', '飲食', '拝観料・入場料', '消費税'])
        # No unmapped-value warning for any of these five known values (the
        # fixture's own pre-existing spacing-damage warnings, unrelated to
        # this field, are not asserted against here).
        self.assertFalse(any('unmapped' in w for w in warnings), warnings)

    def test_zen_journey_shape_maps_one_know_before_you_go_item_to_one_chip(self):
        activity = self._activity(ZEN, knowBeforeYouGoItems=['PUBLIC_TRANSPORTATION_NEARBY'])
        entry = CFG['tours'][str(ZEN)]
        rec, *_ = bokun_source.to_record(activity, activity, [], [], entry, {})
        self.assertEqual(rec['knowChipsEn'], 'Public transport nearby')
        self.assertEqual(rec['knowChipsJa'], '公共交通機関が近い')

    def test_no_enum_values_at_all_stays_empty(self):
        # Ikebana, Candle-making, Swordsmithing: verified empty live.
        activity = self._activity(IKEBANA, inclusions=[], knowBeforeYouGoItems=[])
        entry = CFG['tours'][str(IKEBANA)]
        rec, *_ = bokun_source.to_record(activity, activity, [], [], entry, {})
        self.assertEqual(rec['includedChipsEn'], '')
        self.assertEqual(rec['knowChipsEn'], '')

    def test_enum_chip_labels_are_not_gated_by_ja_reviewed(self):
        # ja_differs=False for these -- they are our own wording (task 18
        # point 4), not Bokun content, so Japanese must be present even on
        # an unreviewed tour.
        activity = self._activity(ZEN, inclusions=['BUS_FARE'])
        entry = dict(CFG['tours'][str(ZEN)], jaReviewed=False)
        rec, *_ = bokun_source.to_record(activity, activity, [], [], entry, {})
        self.assertEqual(rec['includedChipsEn'], 'Bus fare')
        self.assertEqual(rec['includedChipsJa'], 'バス運賃')

    def test_unmapped_enum_value_is_dropped_and_warned_not_rendered_raw(self):
        activity = self._activity(ZEN, inclusions=['BUS_FARE', 'SOME_NEW_ENUM_VALUE'])
        entry = CFG['tours'][str(ZEN)]
        rec, warnings, _ = bokun_source.to_record(activity, activity, [], [], entry, {})
        # The unmapped value never reaches the page as a raw constant.
        self.assertEqual(rec['includedChipsEn'], 'Bus fare')
        self.assertNotIn('SOME_NEW_ENUM_VALUE', rec['includedChipsEn'])
        self.assertNotIn('SOME_NEW_ENUM_VALUE', rec['includedChipsJa'])
        self.assertTrue(any('SOME_NEW_ENUM_VALUE' in w and 'inclusions' in w for w in warnings),
                        warnings)

    def test_unmapped_know_before_you_go_value_is_dropped_and_warned(self):
        activity = self._activity(ZEN, knowBeforeYouGoItems=['SOME_OTHER_ENUM'])
        entry = CFG['tours'][str(ZEN)]
        rec, warnings, _ = bokun_source.to_record(activity, activity, [], [], entry, {})
        self.assertEqual(rec['knowChipsEn'], '')
        self.assertTrue(
            any('SOME_OTHER_ENUM' in w and 'knowBeforeYouGoItems' in w for w in warnings),
            warnings)

    def test_enum_values_are_not_run_through_corrections_or_tracked_as_raw_text(self):
        # Enum constants are API vocabulary, not damaged human text -- they
        # must not appear in the unused-corrections ledger's input.
        activity = self._activity(ZEN, inclusions=['BUS_FARE'])
        entry = CFG['tours'][str(ZEN)]
        rec, warnings, raw_texts = bokun_source.to_record(activity, activity, [], [], entry, {})
        self.assertNotIn('BUS_FARE', ' '.join(raw_texts))


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
            activity, activity_ja, [], [], entry, {})

        self.assertIn('JA-SENTINEL title', rec['titleJa'])
        self.assertIn('JA-SENTINEL excerpt', rec['subJa'])
        self.assertIn('JA-SENTINEL description', rec['ledeJa'])
        self.assertNotEqual(rec['titleJa'], rec['titleEn'])
        self.assertNotEqual(rec['subJa'], rec['subEn'])
        self.assertNotEqual(rec['ledeJa'], rec['ledeEn'])

        # This fixture has none of excluded/requirements/attention, so their
        # chip groups stay empty even on a jaReviewed tour.
        for f in ('notIncludedEn', 'notIncludedJa', 'bringEn', 'bringJa',
                  'knowEn', 'knowJa'):
            self.assertEqual(rec[f], '', f)

    def test_route_ja_is_populated_by_index_when_reviewed(self):
        # The recorded ja fixtures predate localisation and are byte-identical
        # to the English ones, so they can't exercise this path. Build a
        # synthetic ja agendaItems list instead: same length as the English
        # one (3 stops for ikebana), each with a distinguishable, entity-laden
        # title/body so we can prove provenance and that cl() ran on it.
        activity = load(f'activity-{IKEBANA}-EN.json')
        en_items = activity['agendaItems']
        self.assertEqual(len(en_items), 3)
        ja_items = [
            {'title': f'JA-SENTINEL title {i} &amp; more',
             'body': f'JA-SENTINEL body {i} sentinel damage'}
            for i in range(3)
        ]
        activity_ja = dict(activity, agendaItems=ja_items)
        entry = dict(CFG['tours'][str(IKEBANA)], jaReviewed=True)
        corr = {'sentinel damage': 'sentinel fixed'}
        rec, warnings, raw_texts = bokun_source.to_record(
            activity, activity_ja, [], [], entry, corr)

        self.assertEqual(len(rec['route']), 3)
        for i, stop in enumerate(rec['route']):
            self.assertIn(f'JA-SENTINEL title {i}', stop['titleJa'])
            self.assertNotIn('&amp;', stop['titleJa'])
            self.assertIn('&', stop['titleJa'])  # entity decoded, not stripped
            self.assertIn('sentinel fixed', stop['bodyJa'])
            self.assertNotIn('sentinel damage', stop['bodyJa'])
            self.assertNotEqual(stop['titleJa'], stop['title'])
            self.assertNotEqual(stop['bodyJa'], stop['body'])

        # A correction that only fires inside a route step's Japanese must
        # still count as used, or the unused-corrections report would lie
        # to an editor about it being safe to prune. See the English-side
        # equivalent at test_a_correction_only_used_in_an_agenda_item_is_not_reported_as_prunable.
        stale = bokun_text.unused_corrections(raw_texts, corr)
        self.assertNotIn('sentinel damage', stale)

    def test_route_ja_falls_back_when_the_ja_list_is_shorter(self):
        # Only the first of three English stops gets a paired ja stop; the
        # rest must mirror English rather than being left unset, raising, or
        # paired against the wrong (nonexistent) stop.
        activity = load(f'activity-{IKEBANA}-EN.json')
        self.assertEqual(len(activity['agendaItems']), 3)
        ja_items = [{'title': 'JA-SENTINEL title 0', 'body': 'JA-SENTINEL body 0'}]
        activity_ja = dict(activity, agendaItems=ja_items)
        entry = dict(CFG['tours'][str(IKEBANA)], jaReviewed=True)
        rec, warnings, raw_texts = bokun_source.to_record(
            activity, activity_ja, [], [], entry, {})

        route = rec['route']
        self.assertEqual(len(route), 3)
        self.assertIn('JA-SENTINEL title 0', route[0]['titleJa'])
        self.assertNotEqual(route[0]['titleJa'], route[0]['title'])
        for stop in route[1:]:
            self.assertEqual(stop['titleJa'], stop['title'])
            self.assertEqual(stop['bodyJa'], stop['body'])

    def test_route_ja_needs_no_review_flag(self):
        # The ja agendaItems are shown as written -- no flag in front of them.
        activity = load(f'activity-{IKEBANA}-EN.json')
        ja_items = [{'title': f'JA-SENTINEL title {i}', 'body': f'JA-SENTINEL body {i}'}
                    for i in range(len(activity['agendaItems']))]
        activity_ja = dict(activity, agendaItems=ja_items)
        entry = dict(CFG['tours'][str(IKEBANA)])
        rec, warnings, raw_texts = bokun_source.to_record(
            activity, activity_ja, [], [], entry, {})

        for stop in rec['route']:
            self.assertIn('JA-SENTINEL', stop['titleJa'])
            self.assertIn('JA-SENTINEL', stop['bodyJa'])

    def test_price_rows_localise_when_reviewed(self):
        # Task 16: category_ja/rate_title_ja on the price rows are gated by
        # jaReviewed exactly like title/sub/lede/route above -- "do not
        # invent a separate rule". Bokun's recorded fixtures predate
        # localisation, so the Japanese category title and rate title here
        # are built synthetically.
        activity = load(f'activity-{IKEBANA}-EN.json')
        availability = load(f'availability-{IKEBANA}.json')
        activity_ja = dict(activity, pricingCategories=[{'id': 1237647, 'title': '大人様'}])
        availability_ja = [{'rates': [{'id': 2536435, 'title': 'スタンダード貸切グループ'}],
                             'pricesByRate': []}]
        entry = dict(CFG['tours'][str(IKEBANA)], jaReviewed=True)
        rec, warnings, raw_texts = bokun_source.to_record(
            activity, activity_ja, availability, availability_ja, entry, {})

        self.assertTrue(rec['priceRows'])
        for row in rec['priceRows']:
            self.assertEqual(row['category_ja'], '大人様')
        ja_rows = bokun_price.format_full(rec['priceRows'], 'ja')
        self.assertTrue(all('大人様' in r for r in ja_rows))

    def test_price_rows_use_bokuns_japanese_category_titles(self):
        # Bokun's own Japanese category title wins over the hand-written
        # _CAT_JA fallback, with no review flag in front of it.
        activity = load(f'activity-{IKEBANA}-EN.json')
        availability = load(f'availability-{IKEBANA}.json')
        activity_ja = dict(activity, pricingCategories=[{'id': 1237647, 'title': '大人様'}])
        availability_ja = [{'rates': [{'id': 2536435, 'title': 'スタンダード貸切グループ'}],
                             'pricesByRate': []}]
        entry = dict(CFG['tours'][str(IKEBANA)])
        rec, warnings, raw_texts = bokun_source.to_record(
            activity, activity_ja, availability, availability_ja, entry, {})

        for row in rec['priceRows']:
            self.assertEqual(row['category_ja'], '大人様')
        ja_rows = bokun_price.format_full(rec['priceRows'], 'ja')
        self.assertTrue(any('大人様' in r for r in ja_rows))

    def test_group_rate_title_ja_comes_from_the_ja_payload(self):
        # The Zen Journey model: a per-booking (group) row's Japanese label
        # comes from rate_title_ja.
        activity = load(f'activity-{ZEN}-EN.json')
        availability = load(f'availability-{ZEN}.json')
        availability_ja = [{'rates': [{'id': 2536321, 'title': 'ハーフデイ・グループ'},
                                       {'id': 2536324, 'title': 'フルデイ・グループ'}],
                             'pricesByRate': []}]

        entry = dict(CFG['tours'][str(ZEN)])
        rec, *_ = bokun_source.to_record(
            activity, activity, availability, availability_ja, entry, {})
        ja_rows = bokun_price.format_full(rec['priceRows'], 'ja')
        self.assertTrue(any('ハーフデイ・グループ' in r for r in ja_rows))


class FlakyJaAvailabilityClient(FakeClient):
    """Serves the same fixtures as FakeClient, except the Japanese
    availability call for one chosen product either raises or returns None
    -- exercising fetch_records' fallback path (task 16, rule 6: a label is
    not worth failing a build over)."""

    def __init__(self, fail_pid, mode='raise', product_list=None):
        super().__init__(product_list)
        self.fail_pid = fail_pid
        self.mode = mode

    def get(self, path):
        if '/availabilities' in path and 'lang=ja' in path:
            pid = int(path.split('/')[2])
            if pid == self.fail_pid:
                if self.mode == 'raise':
                    raise RuntimeError('simulated Bokun outage')
                return None
        return super().get(path)


class TestJapaneseAvailabilityFetch(unittest.TestCase):
    def test_fetch_records_requests_both_language_availabilities(self):
        c = FakeClient()
        bokun_source.fetch_records(c, CFG)
        avail_paths = [p for p in c.paths if '/availabilities' in p]
        # Four products are asked for English availability; swordsmithing is
        # then held back for having none, so only three reach the Japanese
        # call.
        self.assertEqual(len([p for p in avail_paths if 'lang=EN' in p]), 4)
        self.assertEqual(len([p for p in avail_paths if 'lang=ja' in p]), 3)

    def test_ja_availability_request_failure_falls_back_and_warns(self):
        c = FlakyJaAvailabilityClient(fail_pid=IKEBANA, mode='raise')
        records, warnings = bokun_source.fetch_records(c, CFG)
        self.assertTrue(any('ikebana-ichigo-ichie' in w
                             and 'Japanese availability request failed' in w
                             for w in warnings), warnings)
        by_slug = {r['id']: r for r in records}
        # The build still completes and still prices the tour from English.
        self.assertTrue(by_slug['ikebana-ichigo-ichie']['priceRows'])
        self.assertEqual(by_slug['ikebana-ichigo-ichie']['priceEn'],
                          'from ¥21,000 per adult')

    def test_ja_availability_returning_nothing_falls_back_and_warns(self):
        c = FlakyJaAvailabilityClient(fail_pid=ZEN, mode='none')
        records, warnings = bokun_source.fetch_records(c, CFG)
        self.assertTrue(any('zen-journey' in w and 'returned nothing' in w
                             for w in warnings), warnings)
        by_slug = {r['id']: r for r in records}
        self.assertTrue(by_slug['zen-journey']['priceRows'])
        self.assertEqual(by_slug['zen-journey']['priceEn'], 'from ¥40,000 per group')


class TestGates(unittest.TestCase):
    """The four zero-touch-catalogue gates (spec 3.1-3.4), plus the
    number/area derivations (spec 3.6). All exercised against the real
    recorded fixtures with synthetic overrides -- no new fixture files, per
    the task-3-4 brief -- and always against a scratch registry path, so a
    fixture using a real product id (with an empty registry) can never write
    into the committed cms/tours-slugs.json."""

    def _cfg_without_entry(self, pid):
        """CFG with pid's tours-config.json entry removed entirely (so
        tour_entry(cfg, pid) returns {} -- no slug/number/area override) and
        the allowlist narrowed to just pid, so these single-tour derivation
        tests are never polluted by the other three real tours' ids landing
        in the same scratch registry (which would shift registry-position
        numbering)."""
        tours = dict(CFG['tours'])
        tours.pop(str(pid), None)
        return dict(CFG, tours=tours, allowlist=[pid])

    def _run(self, client, cfg, registry=None):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'r.json')
            if registry is not None:
                tours_slug.save_registry(p, registry)
            records, warnings = bokun_source.fetch_records(client, cfg, registry_path=p)
            final_registry = tours_slug.load_registry(p)
        return records, warnings, final_registry

    # --- Gate 1: tier ---------------------------------------------------

    def test_a_public_tier_product_is_held_back_even_if_listed_and_configured(self):
        c = FakeClient(overrides={f'{ZEN}-EN': {'marketplaceVisibilityType': 'PUBLIC'}})
        records, warnings, _ = self._run(c, CFG, registry=tours_slug.load_registry())
        self.assertNotIn('zen-journey', {r['id'] for r in records})
        self.assertTrue(any(str(ZEN) in w and 'not Zenrise-tier' in w for w in warnings), warnings)

    # --- Gate 2: published (list membership / allowlist fallback) is
    # already covered by TestCatalogue; this confirms it flows through
    # fetch_records and is logged.

    def test_the_resolved_catalogue_is_logged_every_run(self):
        records, warnings, _ = self._run(FakeClient(), CFG, registry=tours_slug.load_registry())
        self.assertTrue(any('resolved catalogue: 3 tour(s)' in w for w in warnings), warnings)
        self.assertTrue(any(f'[{IKEBANA}] -> ikebana-ichigo-ichie' in w for w in warnings), warnings)

    # --- Gate 3: sluggable -----------------------------------------------

    def test_a_new_product_with_no_english_slot_is_held_back_and_named(self):
        # Zen Journey's real fixture has languages=['JA_JP'] -- no 'en' slot.
        # With its config override removed and an empty registry, this is
        # exactly a brand-new, untranslated product.
        cfg = self._cfg_without_entry(ZEN)
        records, warnings, final_registry = self._run(FakeClient(), cfg, registry={})
        self.assertNotIn('zen-journey', {r['id'] for r in records})
        self.assertTrue(any(str(ZEN) in w and 'no resolvable slug' in w
                            and 'The Zen Journey-KAMAKURA' in w for w in warnings), warnings)
        self.assertNotIn(str(ZEN), final_registry)

    def test_a_new_translated_product_derives_and_freezes_its_slug(self):
        cfg = self._cfg_without_entry(ZEN)
        c = FakeClient(overrides={
            f'{ZEN}-EN': {'languages': ['en', 'JA_JP']},
            f'{ZEN}-ja': {'title': 'ZEN-JA-SENTINEL'},
        })
        records, warnings, final_registry = self._run(c, cfg, registry={})
        by_slug = {r['id']: r for r in records}
        self.assertIn('zen-journey', by_slug)
        self.assertTrue(any(f'[{ZEN}] -> zen-journey (slug: derived)' in w for w in warnings), warnings)
        # Frozen: the next build must not recompute it.
        self.assertEqual(final_registry[str(ZEN)], 'zen-journey')

    def test_an_already_frozen_slug_publishes_regardless_of_translation_state(self):
        # Ikebana's real shape: no 'en' language slot at all, yet its slug is
        # already settled in the registry and must not be held back.
        cfg = self._cfg_without_entry(IKEBANA)
        registry = {str(IKEBANA): 'ikebana-ichigo-ichie'}
        records, warnings, _ = self._run(FakeClient(), cfg, registry=registry)
        by_slug = {r['id']: r for r in records}
        self.assertIn('ikebana-ichigo-ichie', by_slug)
        self.assertTrue(any(f'[{IKEBANA}] -> ikebana-ichigo-ichie (slug: registry)' in w
                            for w in warnings), warnings)

    # --- Gate 4: complete --------------------------------------------------

    def test_missing_cover_photo_is_held_back_and_named(self):
        c = FakeClient(overrides={f'{CANDLE}-EN': {'photos': []}})
        records, warnings, _ = self._run(c, CFG, registry=tours_slug.load_registry())
        self.assertNotIn('candle-making', {r['id'] for r in records})
        self.assertTrue(any(str(CANDLE) in w and 'missing cover photo' in w for w in warnings), warnings)

    def test_missing_description_is_held_back_and_named(self):
        c = FakeClient(overrides={f'{IKEBANA}-EN': {'description': ''}})
        records, warnings, _ = self._run(c, CFG, registry=tours_slug.load_registry())
        self.assertNotIn('ikebana-ichigo-ichie', {r['id'] for r in records})
        self.assertTrue(any(str(IKEBANA) in w and 'missing description' in w for w in warnings), warnings)

    def test_an_unbookable_product_is_held_back(self):
        # Swordsmithing's real fixtures are unpriced AND have no availability.
        # It used to publish through the in-preparation layout; since
        # 2026-08-28 an incomplete tour does not publish at all.
        records, warnings, _ = self._run(FakeClient(), CFG, registry=tours_slug.load_registry())
        self.assertNotIn('swordsmithing', {r['id'] for r in records})
        self.assertTrue(any(str(SWORD) in w and 'held back' in w for w in warnings), warnings)

    # --- Derivations: area -------------------------------------------------

    def test_area_falls_back_to_the_trailing_place_dropped_from_the_title(self):
        # Zen Journey's real title ends "-KAMAKURA" and googlePlace is null.
        cfg = self._cfg_without_entry(ZEN)
        cfg['tours'][str(ZEN)] = {'slug': 'zj-area-test'}  # only the slug is an override
        records, warnings, _ = self._run(FakeClient(), cfg, registry={})
        rec = next(r for r in records if r['id'] == 'zj-area-test')
        self.assertEqual(rec['area'], 'Kamakura')

    def test_area_prefers_google_place_city_over_the_title(self):
        cfg = self._cfg_without_entry(ZEN)
        cfg['tours'][str(ZEN)] = {'slug': 'zj-area-test'}
        c = FakeClient(overrides={f'{ZEN}-EN': {'googlePlace': {'city': 'Fujisawa'}}})
        records, warnings, _ = self._run(c, cfg, registry={})
        rec = next(r for r in records if r['id'] == 'zj-area-test')
        self.assertEqual(rec['area'], 'Fujisawa')

    def test_an_underivable_area_holds_the_tour_back_instead_of_crashing(self):
        # No googlePlace, and a title with no trailing place name at all.
        cfg = self._cfg_without_entry(ZEN)
        cfg['tours'][str(ZEN)] = {'slug': 'zj-area-test'}
        c = FakeClient(overrides={f'{ZEN}-EN': {'title': 'The Zen Journey'}})
        records, warnings, _ = self._run(c, cfg, registry={})
        self.assertNotIn('zj-area-test', {r['id'] for r in records})
        self.assertTrue(any(str(ZEN) in w and 'no derivable area' in w for w in warnings), warnings)

    # --- Derivations: number ------------------------------------------------

    def test_number_falls_back_to_the_slugs_registry_position(self):
        cfg = self._cfg_without_entry(ZEN)
        cfg['tours'][str(ZEN)] = {'slug': 'zj-num-test'}  # no explicit number
        registry = {'900001': 'placeholder-one', '900002': 'placeholder-two'}
        records, warnings, final_registry = self._run(FakeClient(), cfg, registry=registry)
        rec = next(r for r in records if r['id'] == 'zj-num-test')
        # zj-num-test is appended after the two seeded placeholders: position 3.
        self.assertEqual(rec['number'], '03')

    def test_explicit_config_number_still_overrides_derivation(self):
        cfg = self._cfg_without_entry(ZEN)
        cfg['tours'][str(ZEN)] = {'slug': 'zj-num-test', 'number': '99'}
        registry = {'900001': 'placeholder-one'}
        records, warnings, _ = self._run(FakeClient(), cfg, registry=registry)
        rec = next(r for r in records if r['id'] == 'zj-num-test')
        self.assertEqual(rec['number'], '99')


class TestConfigEntryIsOptional(unittest.TestCase):
    """A tour the client adds in Bokun and never touches in
    tours-config.json at all must still build (spec 3.6)."""

    def test_a_bokun_id_with_no_config_entry_at_all_still_builds(self):
        cfg = dict(CFG, tours={})
        c = FakeClient(overrides={
            f'{ZEN}-EN': {'languages': ['en', 'JA_JP']},
            f'{ZEN}-ja': {'title': 'ZEN-JA-SENTINEL'},
        })
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'r.json')
            tours_slug.save_registry(p, {})
            records, warnings = bokun_source.fetch_records(c, cfg, registry_path=p)
        by_slug = {r['id']: r for r in records}
        self.assertIn('zen-journey', by_slug)
        # Themes need no config entry either: they come from Bokun's own
        # activityCategories, so a tour added in the panel arrives filterable.
        self.assertEqual(by_slug['zen-journey']['themes'], ['culture', 'walking'])
        self.assertEqual(by_slug['zen-journey']['widgets'], {})


if __name__ == '__main__':
    unittest.main()


class TestProseWithoutBullets(unittest.TestCase):
    """A client may write these fields as bullets OR as paragraphs.

    Bokun's editor allows both, and this product was switched from bullets to
    paragraphs separated in line. With only <li> handled every item collapsed
    into one run-on blob.
    """

    def rec_for(self, included_html):
        activity = dict(load(f'activity-{ZEN}-EN.json'), included=included_html)
        availability = load(f'availability-{ZEN}.json')
        rec, *_ = bokun_source.to_record(
            activity, activity, availability, [], CFG['tours'][str(ZEN)], {})
        return [x for x in rec['includedEn'].split('\n') if x.strip()]

    def test_paragraphs_become_separate_items(self):
        html = ('<p>First thing</p><p>Second thing</p><p>Third thing</p>')
        self.assertEqual(self.rec_for(html), ['First thing', 'Second thing', 'Third thing'])

    def test_trailing_breaks_do_not_create_empty_items(self):
        # the shape this product actually uses
        html = ('<p>First thing<br /><br /></p><p>Second thing<br /><br /></p>')
        self.assertEqual(self.rec_for(html), ['First thing', 'Second thing'])

    def test_leading_breaks_do_not_create_empty_items(self):
        html = '<p>First thing</p><p><br />Second thing</p>'
        self.assertEqual(self.rec_for(html), ['First thing', 'Second thing'])

    def test_bullets_still_win_when_present(self):
        html = '<ul><li>Bullet one</li><li>Bullet two</li></ul><p>Stray paragraph</p>'
        self.assertEqual(self.rec_for(html), ['Bullet one', 'Bullet two'])

    def test_a_single_paragraph_is_one_item(self):
        self.assertEqual(self.rec_for('<p>Only one thing</p>'), ['Only one thing'])


class TestLengthFromJapaneseRates(unittest.TestCase):
    """Rate names are written in Japanese first, so the length must be
    derivable from them alone -- Bokun records no duration per rate, and the
    English name may not exist yet."""

    def rows(self, *ja_titles):
        return [{'rate_title': None, 'rate_title_ja': t} for t in ja_titles]

    def test_half_day_alone(self):
        self.assertEqual(
            bokun_source._length_from_rates(self.rows('グループ（1〜6名）半日')),
            'Half-day')

    def test_full_day_alone(self):
        self.assertEqual(
            bokun_source._length_from_rates(self.rows('グループ（1〜6名）一日')),
            'Full-day')

    def test_both_read_as_both(self):
        self.assertEqual(
            bokun_source._length_from_rates(
                self.rows('グループ（1〜6名）半日', 'グループ（1〜6名）一日')),
            'Full / Half-day')

    def test_the_other_full_day_spellings(self):
        for title in ('1日コース', '終日プラン'):
            self.assertEqual(bokun_source._length_from_rates(self.rows(title)),
                             'Full-day', title)

    def test_japanese_alone_needs_no_english_rate_name(self):
        # The English title is absent entirely, which is the shape a
        # Japanese-first tour has before anyone writes the translation.
        rows = self.rows('半日')
        self.assertIsNone(rows[0]['rate_title'])
        self.assertEqual(bokun_source._length_from_rates(rows), 'Half-day')

    def test_rates_that_say_nothing_return_empty(self):
        self.assertEqual(bokun_source._length_from_rates(self.rows('朝のコース')), '')


class TestLengthWarningIsBilingual(unittest.TestCase):
    def test_the_warning_names_the_japanese_words_too(self):
        # The client writes rate names in Japanese, so telling them to add
        # "Half Day"/"Full Day" sends them to the wrong field.
        base = load(f'activity-{ZEN}-EN.json')
        rates = [dict(r, title=t) for r, t in
                 zip(base['rates'], ('朝のコース', '夕方のコース'))]
        activity = dict(base, rates=rates, durationText='4 hours')
        availability = load(f'availability-{ZEN}.json')
        entry = dict(CFG['tours'][str(ZEN)])
        rec, warnings, _ = bokun_source.to_record(
            activity, activity, availability, [], entry, {})
        nag = [w for w in warnings if 'half- or full-day' in w]
        self.assertTrue(nag, 'the length warning did not fire; test is vacuous')
        self.assertIn('半日', nag[0])
        self.assertIn('一日', nag[0])
