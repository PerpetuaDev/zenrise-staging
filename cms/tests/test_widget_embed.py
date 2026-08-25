# cms/tests/test_widget_embed.py
import importlib.util, os, unittest

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

    def test_records_the_ja_widget_for_later_language_switching(self):
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232',
                                      'ja': f'{CH}/experience-calendar/999'}))
        self.assertIn('data-widget-ja="https://widgets.bokun.io/online-sales/'
                      f'{CH}/experience-calendar/999"', html)

    def test_ja_falls_back_to_en_when_absent(self):
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232'}))
        self.assertNotIn('data-widget-ja', html)

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
        m = bt.tour_model(dict(RECORD, includedEn='Guide\nTea', includedJa='Guide\nTea'))
        html = bt.chips_section(m, {}, {})
        self.assertIn('td_included', html)
        self.assertIn('Guide', html)
        # the three groups Bokun has no data for must not appear at all
        for key in ('td_notinc', 'td_notallowed', 'td_notsuitable'):
            self.assertNotIn(key, html)

    def test_wrapper_only_appears_when_something_is_inside(self):
        m = bt.tour_model(dict(RECORD, includedEn='Guide', includedJa='Guide'))
        self.assertIn('class="chip-groups"', bt.chips_section(m, {}, {}))
        self.assertNotIn('chip-groups', bt.chips_section(bt.tour_model(dict(RECORD)), {}, {}))


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
        self.assertIn('<div class="r-time">30min</div>', html)
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
