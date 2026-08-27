# cms/tests/test_tours_render.py
import importlib.util, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_tours', os.path.join(ROOT, 'cms', 'build-tours.py'))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)


def record(**over):
    r = {'id': 'ikebana-ichigo-ichie', 'bokunId': 1273232, 'number': '01',
         'area': 'Kamakura', 'length': 'Half-day', 'themes': ['Arts & Craft'],
         'cover': {'url': 'https://img/x.jpg'},
         'hoursEn': '1 hour and 30 minutes', 'hoursJa': '1 時間30 分',
         'priceEn': 'from ¥21,000 per adult', 'priceJa': '¥21,000〜（大人おひとり）',
         'priceRows': [{'category': 'Adult', 'min': 3, 'max': 6,
                        'amount': 21000, 'currency': 'JPY'}],
         'widgets': {'en': 'CH/experience-calendar/1273232'}, 'jaReviewed': False,
         'titleEn': 'Ikebana', 'titleJa': 'Ikebana',
         'subEn': 'A private workshop.', 'subJa': 'A private workshop.',
         'ledeEn': 'Ninety minutes with a master.', 'ledeJa': 'Ninety minutes with a master.',
         'coverCaptionEn': '', 'coverCaptionJa': '',
         'includedEn': '', 'includedJa': '', 'notIncludedEn': '', 'notIncludedJa': '',
         'bringEn': '', 'bringJa': '', 'knowEn': '', 'knowJa': '',
         'includedChipsEn': '', 'includedChipsJa': '', 'knowChipsEn': '', 'knowChipsJa': '',
         'route': []}
    r.update(over)
    return r


def model(widgets, full=True, slug='ikebana-ichigo-ichie', price_rows=None):
    return {'id': slug, 'widgets': widgets, 'full': full, 'bokun_id': 1273232,
            'K': 'tours_' + slug, 'price_rows': price_rows or []}


class TestModel(unittest.TestCase):
    def test_priced_product_is_full(self):
        self.assertTrue(bt.tour_model(record())['full'])

    def test_unpriced_product_is_not_full(self):
        self.assertFalse(bt.tour_model(record(priceEn='', priceJa=''))['full'])

    def test_price_text_comes_from_the_record(self):
        m = bt.tour_model(record())
        self.assertEqual(m['price_en'], 'from ¥21,000 per adult')
        self.assertEqual(m['price_ja'], '¥21,000〜（大人おひとり）')

    def test_price_uses_a_per_tour_key_not_a_shared_length_key(self):
        self.assertIsNone(bt.tour_model(record())['price_key'])

    def test_bokun_id_and_widgets_carry_into_the_model(self):
        m = bt.tour_model(record())
        self.assertEqual(m['bokun_id'], 1273232)
        self.assertEqual(m['widgets'], {'en': 'CH/experience-calendar/1273232'})


class TestThemes(unittest.TestCase):
    def test_arts_and_craft_maps_to_a_slug(self):
        self.assertIn('arts', bt.card(bt.tour_model(record())))

    def test_unknown_theme_raises_a_readable_error(self):
        with self.assertRaises(bt.BuildError):
            bt.card(bt.tour_model(record(themes=['Nonexistent Theme'])))


class TestChips(unittest.TestCase):
    """chips() renders short-label content (task 18: Bokun's closed enum
    vocabulary, read via includedChips/knowChips) as <span class="chip">."""

    def test_empty_chip_field_renders_nothing(self):
        m = bt.tour_model(record())
        self.assertEqual(bt.chips(m, 'includedChips', 'inc', {}, {}), '')

    def test_none_field_renders_nothing(self):
        # Not included / What to bring have no enum counterpart in Bokun.
        m = bt.tour_model(record())
        self.assertEqual(bt.chips(m, None, None, {}, {}), '')

    def test_populated_chip_field_renders_items(self):
        m = bt.tour_model(record(includedChipsEn='Bus fare\nTax',
                                 includedChipsJa='バス運賃\n消費税'))
        html = bt.chips(m, 'includedChips', 'inc', {}, {})
        self.assertIn('Bus fare', html)
        self.assertIn('Tax', html)
        self.assertIn('class="chip"', html)


class TestProse(unittest.TestCase):
    """prose() renders free-text sentences (task 18: Bokun's included/
    excluded/requirements/attention fields) as <li>, not <span class="chip">."""

    def test_empty_prose_field_renders_nothing(self):
        m = bt.tour_model(record())
        self.assertEqual(bt.prose(m, 'included', 'incp', {}, {}), '')

    def test_populated_prose_field_renders_list_items(self):
        m = bt.tour_model(record(includedEn='Guide\nEntrance fees',
                                 includedJa='Guide\nEntrance fees'))
        html = bt.prose(m, 'included', 'incp', {}, {})
        self.assertIn('Guide', html)
        self.assertIn('Entrance fees', html)
        self.assertIn('<li ', html)
        self.assertNotIn('class="chip"', html)

    def test_dict_keys_use_the_prose_prefix(self):
        m = bt.tour_model(record(includedEn='Guide', includedJa='ガイド'))
        en, ja = {}, {}
        bt.prose(m, 'included', 'incp', en, ja)
        self.assertEqual(en['tours_ikebana-ichigo-ichie_incp_1'], 'Guide')
        self.assertEqual(ja['tours_ikebana-ichigo-ichie_incp_1'], 'ガイド')


class TestChipGroups(unittest.TestCase):
    """Task 17: the four fixed groups map onto Bokun's own included/excluded/
    requirements/attention fields. notAllowed/notSuitable are retired -- no
    Bokun field ever fed them. Task 18: Included and Good to know also read
    a closed enum vocabulary (inclusions/knowBeforeYouGoItems) as chips, with
    the free-text field rendered as prose alongside; Not included and What
    to bring have no enum counterpart in Bokun, so their chip field/prefix
    are None."""

    def test_chip_groups_are_the_four_bokun_backed_fields(self):
        fields = [g[0] for g in bt.CHIP_GROUPS]
        self.assertEqual(fields, ['included', 'notIncluded', 'bring', 'know'])

    def test_retired_groups_are_gone(self):
        fields = [g[0] for g in bt.CHIP_GROUPS]
        keys = [g[4] for g in bt.CHIP_GROUPS]
        self.assertNotIn('notAllowed', fields)
        self.assertNotIn('notSuitable', fields)
        self.assertNotIn('td_notallowed', keys)
        self.assertNotIn('td_notsuitable', keys)

    def test_new_groups_carry_the_expected_labels_and_keys(self):
        by_field = {g[0]: g for g in bt.CHIP_GROUPS}
        self.assertEqual(by_field['bring'][4:], ('td_bring', 'What to bring'))
        self.assertEqual(by_field['know'][4:], ('td_know', 'Good to know'))

    def test_only_included_and_know_have_an_enum_chip_field(self):
        by_field = {g[0]: g for g in bt.CHIP_GROUPS}
        self.assertEqual(by_field['included'][2:4], ('includedChips', 'inc'))
        self.assertEqual(by_field['know'][2:4], ('knowChips', 'kno'))
        self.assertEqual(by_field['notIncluded'][2:4], (None, None))
        self.assertEqual(by_field['bring'][2:4], (None, None))

    def test_chips_section_renders_the_zen_journey_regression_anchor(self):
        # Zen Journey's real shape (task 18 brief): Included = 5 chips + 9
        # prose; Not included = 4 prose; What to bring = 1 prose; Good to
        # know = 1 chip + 8 prose.
        m = bt.tour_model(record(
            id='zen-journey',
            includedChipsEn='\n'.join(f'Chip {i}' for i in range(5)),
            includedChipsJa='\n'.join(f'チップ {i}' for i in range(5)),
            includedEn='\n'.join(f'Inc {i}' for i in range(9)),
            includedJa='\n'.join(f'Inc {i}' for i in range(9)),
            notIncludedEn='\n'.join(f'Ninc {i}' for i in range(4)),
            notIncludedJa='\n'.join(f'Ninc {i}' for i in range(4)),
            bringEn='Bring 0', bringJa='Bring 0',
            knowChipsEn='Know chip 0', knowChipsJa='知るチップ 0',
            knowEn='\n'.join(f'Know {i}' for i in range(8)),
            knowJa='\n'.join(f'Know {i}' for i in range(8))))
        en, ja = {}, {}
        chips_html = bt.chips_section(m, en, ja)
        other_html = bt.other_info_section(m, en, ja)
        html = chips_html + other_html
        for key in ('td_included', 'td_notinc', 'td_bring', 'td_know'):
            self.assertIn(key, html)
        # chips under the lede, prose below the route -- never mixed
        self.assertNotIn('class="prose"', chips_html)
        self.assertNotIn('class="chip"', other_html)
        self.assertEqual(sum(1 for v in en if v.startswith('tours_zen-journey_inc_')), 5)
        self.assertEqual(sum(1 for v in en if v.startswith('tours_zen-journey_incp_')), 9)
        self.assertEqual(sum(1 for v in en if v.startswith('tours_zen-journey_nincp_')), 4)
        self.assertEqual(sum(1 for v in en if v.startswith('tours_zen-journey_brgp_')), 1)
        self.assertEqual(sum(1 for v in en if v.startswith('tours_zen-journey_kno_')), 1)
        self.assertEqual(sum(1 for v in en if v.startswith('tours_zen-journey_knop_')), 8)
        self.assertEqual(html.count('class="chip"'), 6)
        self.assertEqual(html.count('<li '), 22)

    def test_a_tour_with_all_fields_empty_renders_no_chip_groups(self):
        # Candle-making and Swordsmithing: no groups at all.
        m = bt.tour_model(record())
        self.assertEqual(bt.chips_section(m, {}, {}), '')

    def test_a_prose_only_group_lands_in_other_info_not_under_the_lede(self):
        # Not included / What to bring never have a chip field.
        m = bt.tour_model(record(notIncludedEn='A', notIncludedJa='A'))
        self.assertEqual(bt.chips_section(m, {}, {}), '')
        other = bt.other_info_section(m, {}, {})
        self.assertIn('<li ', other)
        self.assertNotIn('class="chip"', other)

    def test_a_group_with_only_chips_renders_no_prose_markup(self):
        m = bt.tour_model(record(includedChipsEn='Bus fare', includedChipsJa='バス運賃'))
        html = bt.chips_section(m, {}, {})
        self.assertIn('class="chip"', html)
        self.assertNotIn('<ul class="prose">', html)

    def test_one_group_splits_across_the_two_sections(self):
        # "Included" commonly has both kinds: the chips belong under the lede,
        # the sentences below the route.
        m = bt.tour_model(record(
            includedChipsEn='Bus fare', includedChipsJa='バス運賃',
            includedEn='A guide', includedJa='ガイド'))
        chips_html = bt.chips_section(m, {}, {})
        other_html = bt.other_info_section(m, {}, {})
        self.assertIn('class="chips"', chips_html)
        self.assertNotIn('class="prose"', chips_html)
        self.assertIn('class="prose"', other_html)
        self.assertNotIn('class="chips"', other_html)
        # both still carry the group's own heading
        self.assertIn('td_included', chips_html)
        self.assertIn('td_included', other_html)

    def test_other_info_is_a_titled_section_or_nothing(self):
        m = bt.tour_model(record(notIncludedEn='A', notIncludedJa='A'))
        self.assertIn('td_other', bt.other_info_section(m, {}, {}))
        self.assertIn('class="other-wrap"', bt.other_info_section(m, {}, {}))
        # a tour with no prose at all must not render an empty heading
        self.assertEqual(bt.other_info_section(bt.tour_model(record()), {}, {}), '')


class TestCardAndTile(unittest.TestCase):
    def test_card_links_to_the_slug(self):
        self.assertIn('href="tour-ikebana-ichigo-ichie.html"', bt.card(bt.tour_model(record())))

    def test_card_shows_the_from_price(self):
        self.assertIn('from ¥21,000 per adult', bt.card(bt.tour_model(record())))

    def test_card_for_unpriced_tour_shows_no_price_text(self):
        html = bt.card(bt.tour_model(record(priceEn='', priceJa='')))
        self.assertNotIn('¥', html)

    def test_tile_links_to_the_slug(self):
        self.assertIn('href="tour-ikebana-ichigo-ichie.html"', bt.tile(bt.tour_model(record())))


class TestStopTime(unittest.TestCase):
    def test_extracts_a_leading_duration(self):
        self.assertEqual(bt.split_stop_time('30min The history of the art.'),
                         ('30min', 'The history of the art.'))

    def test_handles_spaced_and_long_forms(self):
        for raw, want in [('30 mins: Arranging.', ('30 mins', 'Arranging.')),
                          ('1 hour - Tea.', ('1 hour', 'Tea.')),
                          ('90 minutes · Workshop.', ('90 minutes', 'Workshop.'))]:
            self.assertEqual(bt.split_stop_time(raw), want)

    def test_no_duration_returns_none_and_the_body_intact(self):
        self.assertEqual(bt.split_stop_time('Meet at the gate.'),
                         (None, 'Meet at the gate.'))

    def test_does_not_eat_a_leading_number_that_is_not_a_duration(self):
        self.assertEqual(bt.split_stop_time('3 temples on the northern route.'),
                         (None, '3 temples on the northern route.'))

    def test_timed_row_renders_a_time_cell(self):
        # route_section() belongs to Task 8; route_rows() already carries the
        # per-row markup this exercises.
        m = dict(model({}), full=True,
                 route=[{'title': 'History', 'body': '30min The Sogetsu school.'}])
        html = bt.route_rows(m, {}, {})
        # The time cell is translatable, so it carries a data-i18n key.
        self.assertIn('class="r-time"', html)
        self.assertIn('>30min</div>', html)
        self.assertIn('_rt_01_time"', html)
        self.assertNotIn('no-time', html)

    def test_untimed_row_omits_the_cell_and_marks_the_row(self):
        m = dict(model({}), full=True,
                 route=[{'title': 'Arriving', 'body': 'Meet at the gate.'}])
        html = bt.route_rows(m, {}, {})
        self.assertNotIn('r-time', html)
        self.assertIn('class="r-row no-time"', html)

    def test_duration_is_stripped_from_the_note_text(self):
        m = dict(model({}), full=True,
                 route=[{'title': 'History', 'body': '30min The Sogetsu school.'}])
        en = {}
        bt.route_rows(m, en, {})
        self.assertEqual(en['tours_ikebana-ichigo-ichie_rt_01_note'],
                         'The Sogetsu school.')


# Ikebana's real shape: several single-count tiers at the same amount plus
# one lower-guest-count tier at a higher amount (task 14).
IKEBANA_ROWS = [
    {'category': 'Adults', 'min': 5, 'max': 5, 'amount': 21000, 'currency': 'JPY'},
    {'category': 'Adults', 'min': 4, 'max': 4, 'amount': 21000, 'currency': 'JPY'},
    {'category': 'Adults', 'min': 6, 'max': 6, 'amount': 21000, 'currency': 'JPY'},
    {'category': 'Adults', 'min': 3, 'max': 3, 'amount': 21000, 'currency': 'JPY'},
    {'category': 'Adults', 'min': 1, 'max': 2, 'amount': 44000, 'currency': 'JPY'},
]
# The Zen Journey's real shape: two per-booking rates, distinguished only by
# rate title.
ZEN_ROWS = [
    {'category': None, 'min': 1, 'max': 6, 'amount': 40000, 'currency': 'JPY',
     'per_booking': True, 'rate_title': 'Group(1~6) Harf Day'},
    {'category': None, 'min': 1, 'max': 6, 'amount': 70000, 'currency': 'JPY',
     'per_booking': True, 'rate_title': 'Group(1~6) Full Day'},
]


class TestPriceBreakdownBlock(unittest.TestCase):
    """task 14: the breakdown rendered above the booking widget."""

    def test_hidden_when_every_row_shares_the_headline_amount(self):
        m = model({}, price_rows=[
            {'category': 'Adult', 'min': 1, 'max': 6, 'amount': 21000, 'currency': 'JPY'}])
        self.assertEqual(bt.price_breakdown_block(m, {}, {}), '')

    def test_hidden_when_there_are_no_price_rows(self):
        m = model({}, price_rows=[])
        self.assertEqual(bt.price_breakdown_block(m, {}, {}), '')

    def test_renders_a_row_per_distinct_amount_for_ikebana(self):
        m = model({}, price_rows=IKEBANA_ROWS)
        en, ja = {}, {}
        html = bt.price_breakdown_block(m, en, ja)
        self.assertIn('¥44,000', html)
        self.assertIn('¥21,000', html)
        # merged into one row per amount, not five rows
        self.assertEqual(html.count('class="pb-row"'), 2)

    def test_zen_journey_rows_are_distinguished_by_rate_title_not_both_group(self):
        m = model({}, slug='zen-journey', price_rows=ZEN_ROWS)
        en, ja = {}, {}
        html = bt.price_breakdown_block(m, en, ja)
        self.assertIn('Group(1~6) Harf Day', html)
        self.assertIn('Group(1~6) Full Day', html)
        self.assertEqual(html.count('class="pb-row"'), 2)

    def test_rows_are_written_into_both_i18n_dicts_with_the_k_prefixed_key(self):
        m = model({}, slug='zen-journey', price_rows=ZEN_ROWS)
        en, ja = {}, {}
        bt.price_breakdown_block(m, en, ja)
        self.assertIn('tours_zen-journey_pb_1', en)
        self.assertIn('tours_zen-journey_pb_1', ja)
        self.assertIn('tours_zen-journey_pb_note', en)
        self.assertIn('tours_zen-journey_pb_note', ja)

    def test_rows_use_data_i18n_html_so_the_language_toggle_can_swap_them(self):
        m = model({}, slug='zen-journey', price_rows=ZEN_ROWS)
        html = bt.price_breakdown_block(m, {}, {})
        self.assertIn('data-i18n-html="tours_zen-journey_pb_1"', html)

    def test_sample_tour_shaped_rows_with_no_rate_title_do_not_crash(self):
        # The staging-only sample tour has hand-written per-person priceRows
        # with no rate titles.
        m = model({}, slug='yokohama-harbour-evening', price_rows=[
            {'category': 'Adult', 'min': 1, 'max': 6, 'amount': 18000, 'currency': 'JPY'},
            {'category': 'Child', 'min': 1, 'max': 6, 'amount': 9000, 'currency': 'JPY'},
        ])
        html = bt.price_breakdown_block(m, {}, {})
        self.assertIn('¥18,000', html)
        self.assertIn('¥9,000', html)


class TestWidgetBlockPlacesBreakdown(unittest.TestCase):
    def test_breakdown_sits_above_the_widget_mount(self):
        m = model({'en': 'CH/experience-calendar/1273232'}, price_rows=IKEBANA_ROWS)
        price_html = bt.price_breakdown_block(m, {}, {})
        html = bt.widget_block(m, price_html)
        self.assertLess(html.index('price-breakdown'), html.index('bokunWidget'))

    def test_breakdown_sits_above_the_missing_widget_placeholder_too(self):
        m = model({}, price_rows=IKEBANA_ROWS)
        price_html = bt.price_breakdown_block(m, {}, {})
        html = bt.widget_block(m, price_html)
        self.assertLess(html.index('price-breakdown'),
                        html.index('Booking widget not yet configured'))

    def test_no_price_html_leaves_widget_block_unchanged(self):
        m = model({'en': 'CH/experience-calendar/1273232'})
        self.assertNotIn('price-breakdown', bt.widget_block(m))


class TestPrepTemplateUnaffected(unittest.TestCase):
    """The in-preparation layout has no booking widget and must render no
    price breakdown either (task 14)."""

    def setUp(self):
        self.tpl_full = bt.load_template('tour-detail.html')
        self.tpl_prep = bt.load_template('tour-prep.html')

    def test_unpriced_tour_renders_via_the_prep_template_with_no_breakdown(self):
        m = bt.tour_model(record(priceEn='', priceJa='', priceRows=[]))
        html = bt.render_detail(m, self.tpl_full, self.tpl_prep)
        self.assertNotIn('price-breakdown', html)
        self.assertNotIn('id="book"', html)

    def test_priced_tour_with_a_real_breakdown_renders_via_the_full_template(self):
        m = bt.tour_model(record(priceRows=IKEBANA_ROWS))
        html = bt.render_detail(m, self.tpl_full, self.tpl_prep)
        self.assertIn('price-breakdown', html)
        self.assertIn('id="book"', html)


class TestGridOrder(unittest.TestCase):
    """The grid must read in sequence, whatever order Bokun returns.

    The Website product list's member order is the client's to change and bears
    no relation to the eyebrow numbering, so a build that renders in catalogue
    order produces a grid reading 02, 03, 01.
    """

    def _numbers(self, page):
        with open(os.path.join(ROOT, page), encoding='utf-8') as f:
            html = f.read()
        return [m.group(1) for m in re.finditer(
            r'href="tour-[a-z0-9-]+\.html".*?No\.\s*(\d+)', html, re.S)]

    def test_cards_render_in_ascending_number_order(self):
        for page in ('tours.html', 'index.html'):
            nums = self._numbers(page)
            self.assertTrue(nums, page)
            self.assertEqual(nums, sorted(nums), page)

    def test_sort_key_puts_unnumbered_tours_last(self):
        models = [{'num': ''}, {'num': '03'}, {'num': '01'}]
        models.sort(key=lambda m: (m['num'] == '', m['num']))
        self.assertEqual([m['num'] for m in models], ['01', '03', ''])


class TestLedeParagraphs(unittest.TestCase):
    """The description keeps Bokun's paragraphing: first large, rest reduced."""

    def block(self, paras_en, paras_ja=None, joined=''):
        en, ja = {}, {}
        m = bt.tour_model(record(ledeParasEn=paras_en,
                                 ledeParasJa=paras_ja if paras_ja is not None else paras_en,
                                 ledeEn=joined or ' '.join(paras_en),
                                 ledeJa=joined or ' '.join(paras_en)))
        return bt.lede_block(m, en, ja), en, ja

    def test_first_paragraph_leads_and_the_rest_are_reduced(self):
        html, _, _ = self.block(['One.', 'Two.', 'Three.'])
        self.assertEqual(html.count('class="lede"'), 1)
        self.assertEqual(html.count('class="lede-sub"'), 2)
        self.assertLess(html.index('class="lede"'), html.index('class="lede-sub"'))

    def test_a_single_paragraph_emits_no_sub_paragraph(self):
        html, _, _ = self.block(['Only one.'])
        self.assertIn('class="lede"', html)
        self.assertNotIn('lede-sub', html)

    def test_every_paragraph_is_keyed_in_both_languages(self):
        _, en, ja = self.block(['One.', 'Two.', 'Three.'])
        self.assertEqual(sorted(en), sorted(ja))
        self.assertEqual(len(en), 3)

    def test_keys_are_numbered_from_two(self):
        _, en, _ = self.block(['One.', 'Two.'])
        self.assertIn('tours_ikebana-ichigo-ichie_lede', en)
        self.assertIn('tours_ikebana-ichigo-ichie_lede_2', en)

    def test_japanese_running_short_falls_back_to_english(self):
        _, en, ja = self.block(['One.', 'Two.', 'Three.'], paras_ja=['\u4e00\u3002'])
        self.assertEqual(ja['tours_ikebana-ichigo-ichie_lede'], '\u4e00\u3002')
        # the two English paragraphs Japanese does not cover stand in unchanged
        self.assertEqual(ja['tours_ikebana-ichigo-ichie_lede_2'], 'Two.')
        self.assertEqual(ja['tours_ikebana-ichigo-ichie_lede_3'], 'Three.')

    def test_falls_back_to_the_joined_lede_for_an_older_cache(self):
        # cache entries written before ledeParas existed carry only the string
        html, en, _ = self.block([], joined='A single joined lede.')
        self.assertIn('class="lede"', html)
        self.assertNotIn('lede-sub', html)
        self.assertEqual(en['tours_ikebana-ichigo-ichie_lede'], 'A single joined lede.')

    def test_paragraph_text_is_escaped(self):
        html, _, _ = self.block(['Quotes "here" & ampersands'])
        self.assertNotIn('"here"', html.split('data-i18n')[1])
        self.assertIn('&amp;', html)


if __name__ == '__main__':
    unittest.main()
