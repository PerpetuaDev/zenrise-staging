# cms/tests/test_tours_render.py
import importlib.util, os, unittest

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
         'notAllowedEn': '', 'notAllowedJa': '', 'notSuitableEn': '', 'notSuitableJa': '',
         'route': []}
    r.update(over)
    return r


def model(widgets, full=True, slug='ikebana-ichigo-ichie'):
    return {'id': slug, 'widgets': widgets, 'full': full, 'bokun_id': 1273232,
            'K': 'tours_' + slug}


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
    def test_empty_chip_field_renders_nothing(self):
        m = bt.tour_model(record())
        self.assertEqual(bt.chips(m, 'included', 'inc', {}, {}), '')

    def test_populated_chip_field_renders_items(self):
        m = bt.tour_model(record(includedEn='Guide\nEntrance fees',
                                 includedJa='Guide\nEntrance fees'))
        html = bt.chips(m, 'included', 'inc', {}, {})
        self.assertIn('Guide', html)
        self.assertIn('Entrance fees', html)


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
        self.assertIn('<div class="r-time">30min</div>', html)
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


if __name__ == '__main__':
    unittest.main()
