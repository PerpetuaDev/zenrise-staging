# cms/tests/test_widget_embed.py
import glob, importlib.util, json, os, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_tours', os.path.join(ROOT, 'cms', 'build-tours.py'))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)

CH = 'e2350ad8-80af-4c18-a21a-acae6d72283f'

# A Bokun-shaped record with no inclusions and no route, as three of the four
# real tours actually are.
RECORD = {'id': 'ikebana-ichigo-ichie', 'bokunId': 1273232, 'number': '01',
          'area': 'Kamakura', 'length': 'Half-day', 'themes': ['Arts & Craft'],
          'cover': {'url': 'https://img/x.jpg'},
          'hoursEn': '1 hour and 30 minutes', 'hoursJa': '1 時間30 分',
          'priceEn': 'from ¥21,000 per adult', 'priceJa': '¥21,000〜（大人おひとり）',
          'priceRows': [], 'widgets': {}, 'jaReviewed': False,
          'titleEn': 'Ikebana', 'titleJa': 'Ikebana',
          'subEn': 'A private workshop.', 'subJa': 'A private workshop.',
          'ledeEn': 'Ninety minutes.', 'ledeJa': 'Ninety minutes.',
          'coverCaptionEn': '', 'coverCaptionJa': '',
          'includedEn': '', 'includedJa': '', 'notIncludedEn': '', 'notIncludedJa': '',
          'notAllowedEn': '', 'notAllowedJa': '', 'notSuitableEn': '', 'notSuitableJa': '',
          'route': []}


def model(widgets, full=True, slug='ikebana-ichigo-ichie'):
    return {'id': slug, 'widgets': widgets, 'full': full, 'bokun_id': 1273232,
            'K': 'tours_' + slug}


class TestWidgetBlock(unittest.TestCase):
    def test_emits_loader_and_mount_for_the_en_widget(self):
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232'}))
        self.assertIn('BokunWidgetsLoader.js?bookingChannelUUID=' + CH, html)
        self.assertIn('class="bokunWidget"', html)
        self.assertIn(f'https://widgets.bokun.io/online-sales/{CH}/experience-calendar/1273232',
                      html)

    def test_language_is_pinned_on_data_src_not_a_second_widget(self):
        # Bokun's widget app reads a `lang` param off data-src, so ONE widget
        # serves both languages. A separate ja widget is no longer needed, and
        # the obsolete data-widget-ja attribute must not come back.
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232'}))
        base = f'https://widgets.bokun.io/online-sales/{CH}/experience-calendar/1273232'
        self.assertIn(f'data-src="{base}?lang=en"', html)
        self.assertIn(f'data-widget-base="{base}"', html)
        self.assertNotIn('data-widget-ja', html)

    def test_the_stored_language_is_applied_before_the_async_loader_runs(self):
        # the loader reads the mount once; if it wins the race the calendar is
        # stuck in the wrong language until a manual refresh
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232'}))
        set_lang = html.index("localStorage.getItem('zenrise-lang')")
        loader = html.index('BokunWidgetsLoader.js')
        self.assertLess(set_lang, loader)

    def test_a_language_change_reloads_the_page(self):
        # Re-mounting in place was tried and abandoned: the swap works and the
        # new iframe carries lang=ja, but it hangs at the loader's 700px
        # placeholder because Bokun's app script does not re-handshake for a
        # second mount. A reload is deterministic.
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232'}))
        self.assertIn('ZenriseI18n', html)
        self.assertIn('onChange', html)
        self.assertIn('window.location.reload()', html)

    def test_the_reload_is_guarded_so_it_cannot_loop(self):
        # Reloading unconditionally on a language event would re-fire on the way
        # back in. The guard compares against what the mount actually rendered.
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232'}))
        self.assertIn("getAttribute('data-widget-lang') !== want", html)
        # and it must do nothing when no widget is mounted
        self.assertIn('if (m &&', html)

    def test_no_in_place_remount_survives(self):
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232'}))
        self.assertNotIn('replaceChild', html)
        self.assertNotIn('createElement(\'div\')', html)

    def test_a_stale_config_ja_path_is_ignored_rather_than_emitted(self):
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232',
                                      'ja': f'{CH}/experience-calendar/999'}))
        self.assertNotIn('experience-calendar/999', html)

    def test_noscript_points_at_the_go_redirect(self):
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232'}))
        self.assertIn('<noscript>', html)
        self.assertIn('go/ikebana-ichigo-ichie', html)

    def test_no_widget_configured_yields_a_visible_placeholder_not_silence(self):
        html = bt.widget_block(model({}))
        self.assertIn('data-widget-missing', html)
        self.assertNotIn('bokunWidget', html)

    def test_unpriced_tour_gets_no_widget(self):
        self.assertEqual(bt.widget_block(model({'en': 'x/y/1'}, full=False)), '')

    def test_book_anchor_resolves_in_both_the_widget_and_placeholder_branches(self):
        # The bottom CTA links to #book in every rendering of the full template,
        # so both branches of widget_block must expose id="book" or the anchor
        # target does not exist wherever a tour has no widget configured yet.
        configured = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232'}))
        placeholder = bt.widget_block(model({}))
        self.assertIn('id="book"', configured)
        self.assertIn('id="book"', placeholder)


class TestTemplate(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, 'cms', 'templates', 'tour-detail.html')) as f:
            self.tpl = f.read()

    def test_template_has_a_widget_slot(self):
        self.assertIn('{{WIDGET_BLOCK}}', self.tpl)

    def test_custom_calendar_markup_is_gone(self):
        self.assertNotIn('aside class="cal"', self.tpl)
        self.assertNotIn('id="cal-days"', self.tpl)

    def test_custom_calendar_script_is_gone(self):
        self.assertNotIn('cal-go', self.tpl)
        self.assertNotIn('zenrise-booking-v1', self.tpl)

    def test_no_stale_template_slots_remain(self):
        for slot in ('{{CAL_PRICE}}',):
            self.assertNotIn(slot, self.tpl, f'{slot} left behind after calendar removal')

    def test_route_is_a_whole_section_slot_not_just_rows(self):
        # A tour with no agendaItems must render no route heading either.
        self.assertIn('{{ROUTE_SECTION}}', self.tpl)
        self.assertNotIn('{{ROUTE_ROWS}}', self.tpl)


class TestChipsSection(unittest.TestCase):
    def test_no_chips_at_all_renders_nothing(self):
        m = bt.tour_model(dict(RECORD))
        self.assertEqual(bt.chips_section(m, {}, {}), '')

    def test_only_populated_groups_are_rendered(self):
        # free text, so this is Other info rather than chips
        m = bt.tour_model(dict(RECORD, includedEn='Guide\nTea', includedJa='Guide\nTea'))
        html = bt.other_info_section(m, {}, {})
        self.assertIn('td_included', html)
        self.assertIn('Guide', html)
        # the three groups Bokun has no data for must not appear at all
        for key in ('td_notinc', 'td_notallowed', 'td_notsuitable'):
            self.assertNotIn(key, html)

    def test_wrapper_only_appears_when_something_is_inside(self):
        m = bt.tour_model(dict(RECORD, includedEn='Guide', includedJa='Guide'))
        self.assertIn('class="chip-groups"', bt.other_info_section(m, {}, {}))
        empty = bt.tour_model(dict(RECORD))
        self.assertNotIn('chip-groups', bt.other_info_section(empty, {}, {}))
        self.assertNotIn('chip-groups', bt.chips_section(empty, {}, {}))

    def test_the_template_has_a_slot_for_other_info_after_the_route(self):
        tpl = bt.load_template('tour-detail.html')
        self.assertIn('{{OTHER_INFO_SECTION}}', tpl)
        self.assertLess(tpl.index('{{ROUTE_SECTION}}'),
                        tpl.index('{{OTHER_INFO_SECTION}}'))
        # and the chips stay above, inside the lede column
        self.assertLess(tpl.index('{{CHIPS_SECTION}}'),
                        tpl.index('{{ROUTE_SECTION}}'))


class TestRouteSection(unittest.TestCase):
    def test_route_section_is_empty_when_there_are_no_stops(self):
        m = dict(model({}), route=[], full=True)
        self.assertEqual(bt.route_section(m, {}, {}), '')

    def test_route_section_renders_heading_and_rows_when_there_are_stops(self):
        m = dict(model({}), route=[{'title': 'Arriving', 'body': 'Meet at the gate.'}],
                 full=True)
        html = bt.route_section(m, {}, {})
        self.assertIn('Arriving', html)
        self.assertIn('Meet at the gate.', html)
        # Must reproduce the template's real wrapper, not an invented one.
        self.assertIn('class="route-wrap"', html)
        self.assertIn('<div class="route">', html)
        self.assertIn('data-i18n="td_route"', html)

    def test_route_rows_number_stops_from_one(self):
        m = dict(model({}), full=True, route=[
            {'title': 'First', 'body': 'a'}, {'title': 'Second', 'body': 'b'}])
        en, ja = {}, {}
        bt.route_section(m, en, ja)
        self.assertIn('tours_ikebana-ichigo-ichie_rt_01_name', en)
        self.assertIn('tours_ikebana-ichigo-ichie_rt_02_name', en)
        self.assertEqual(en['tours_ikebana-ichigo-ichie_rt_02_name'], 'Second')

    def test_route_rows_fill_the_ja_dict_too(self):
        m = dict(model({}), full=True, route=[{'title': 'First', 'body': 'a'}])
        en, ja = {}, {}
        bt.route_section(m, en, ja)
        self.assertEqual(ja['tours_ikebana-ichigo-ichie_rt_01_name'], 'First')


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
        m = dict(model({}), full=True,
                 route=[{'title': 'History', 'body': '30min The Sogetsu school.'}])
        html = bt.route_section(m, {}, {})
        # The time cell is translatable, so it carries a data-i18n key.
        self.assertIn('class="r-time"', html)
        self.assertIn('>30min</div>', html)
        self.assertIn('_rt_01_time"', html)
        self.assertNotIn('no-time', html)

    def test_untimed_row_omits_the_cell_and_marks_the_row(self):
        m = dict(model({}), full=True,
                 route=[{'title': 'Arriving', 'body': 'Meet at the gate.'}])
        html = bt.route_section(m, {}, {})
        self.assertNotIn('r-time', html)
        self.assertIn('class="r-row no-time"', html)

    def test_duration_is_stripped_from_the_note_text(self):
        m = dict(model({}), full=True,
                 route=[{'title': 'History', 'body': '30min The Sogetsu school.'}])
        en = {}
        bt.route_section(m, en, {})
        self.assertEqual(en['tours_ikebana-ichigo-ichie_rt_01_note'],
                         'The Sogetsu school.')


if __name__ == '__main__':
    unittest.main()


class TestWidgetPathIsDerivable(unittest.TestCase):
    """A newly listed tour must get a booking calendar with no developer step.

    Bokun renders a calendar for any product in the channel at
    <channel>/experience-calendar/<productId>, with no per-product setup in the
    panel -- verified against products that never had a widget configured. Before
    this, a new tour published with "Booking widget not yet configured".
    """

    def setUp(self):
        with open(os.path.join(ROOT, 'cms', 'tours-config.json')) as f:
            self.cfg = json.load(f)
        self.samples = {s['id'] for s in (self.cfg.get('sampleTours') or [])}

    def test_the_channel_uuid_is_configured(self):
        self.assertTrue((self.cfg.get('bookingChannelUUID') or '').strip(),
                        'bookingChannelUUID is what makes the path derivable')

    def test_every_real_tour_page_has_a_mounted_widget(self):
        for path in glob.glob(os.path.join(ROOT, 'tour-*.html')):
            slug = os.path.basename(path)[len('tour-'):-len('.html')]
            if slug in self.samples:
                continue
            html = open(path, encoding='utf-8').read()
            self.assertIn('class="bokunWidget"', html, slug)
            self.assertNotIn('data-widget-missing', html, slug)

    def test_sample_tours_do_not_get_a_derived_widget(self):
        # they carry an invented bokunId, so a derived URL would point at a
        # product that does not exist
        for slug in self.samples:
            path = os.path.join(ROOT, f'tour-{slug}.html')
            if not os.path.exists(path):
                continue
            html = open(path, encoding='utf-8').read()
            self.assertNotIn('data-widget-base', html, slug)
