# cms/tests/test_tours_filters.py
import importlib.util, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_tours', os.path.join(ROOT, 'cms', 'build-tours.py'))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)


def m(area='Kamakura', themes=()):
    return {'area': area, 'themes': list(themes)}


def chips(html, attr):
    return re.findall(rf'data-{attr}="([^"]+)"', html)


class TestThemeSlugValidation(unittest.TestCase):
    """Config and Bokun both speak slugs now, so this is a gate, not a map."""

    def test_known_slugs_pass_through(self):
        self.assertEqual(bt.theme_slugs(['walking', 'arts']), ['walking', 'arts'])

    def test_a_retired_slug_is_rejected(self):
        # 'local' has no Bokun source and stays retired; a config entry still
        # carrying it must fail loudly rather than render a dead chip.
        with self.assertRaises(bt.BuildError):
            bt.theme_slugs(['local'])

    def test_temples_is_a_live_slug_again(self):
        # Reinstated once PILGRIMAGE_OR_RELIGION turned up in the vocabulary.
        self.assertEqual(bt.theme_slugs(['temples']), ['temples'])


class TestThemeRow(unittest.TestCase):
    def test_a_chip_per_distinct_theme_present(self):
        html = bt.filter_rows([m(themes=['arts']), m(themes=['walking'])])
        self.assertEqual(chips(html, 'theme'), ['arts', 'walking'])

    def test_chip_order_is_canonical_not_catalogue_order(self):
        html = bt.filter_rows([m(themes=['walking']), m(themes=['temples']),
                               m(themes=['arts'])])
        self.assertEqual(chips(html, 'theme'), ['temples', 'arts', 'walking'])

    def test_no_chip_for_a_theme_no_tour_has(self):
        html = bt.filter_rows([m(themes=['arts']), m(themes=['walking'])])
        self.assertNotIn('data-theme="culture"', html)

    def test_row_is_omitted_when_only_one_theme_is_present(self):
        # A lone chip filters nothing: everything it can show is already shown.
        html = bt.filter_rows([m(themes=['arts']), m(themes=['arts'])])
        self.assertEqual(chips(html, 'theme'), [])

    def test_chips_carry_their_i18n_key(self):
        html = bt.filter_rows([m(themes=['arts']), m(themes=['walking'])])
        self.assertIn('data-i18n="tours_theme_arts"', html)
        self.assertIn('data-i18n="tours_theme_walking"', html)


class TestAreaRow(unittest.TestCase):
    def test_row_is_omitted_when_every_tour_shares_one_area(self):
        # Today's live catalogue: three tours, all Kamakura.
        html = bt.filter_rows([m(area='Kamakura', themes=['arts']),
                               m(area='Kamakura', themes=['walking'])])
        self.assertEqual(chips(html, 'area'), [])

    def test_all_areas_is_pinned_first_and_active(self):
        html = bt.filter_rows([m(area='Kamakura'), m(area='Yokohama')])
        self.assertEqual(chips(html, 'area'), ['all', 'kamakura', 'yokohama'])
        self.assertIn('class="chip on" data-area="all"', html)

    def test_area_order_is_canonical_not_catalogue_order(self):
        html = bt.filter_rows([m(area='Yokohama'), m(area='Enoshima'),
                               m(area='Kamakura')])
        self.assertEqual(chips(html, 'area'),
                         ['all', 'kamakura', 'enoshima', 'yokohama'])

    def test_an_area_with_no_i18n_key_is_rejected(self):
        with self.assertRaises(bt.BuildError):
            bt.filter_rows([m(area='Fujisawa'), m(area='Kamakura')])


class TestSectionLabel(unittest.TestCase):
    """The label has to describe the rows that actually rendered."""

    def test_label_reads_by_area_when_the_area_row_is_there(self):
        html = bt.filter_rows([m(area='Kamakura'), m(area='Yokohama')])
        self.assertIn('data-i18n="tours_filter_label"', html)

    def test_label_switches_to_experience_when_only_themes_render(self):
        html = bt.filter_rows([m(themes=['arts']), m(themes=['walking'])])
        self.assertIn('data-i18n="tours_filter_label_theme"', html)
        self.assertNotIn('data-i18n="tours_filter_label"', html)

    def test_no_label_when_no_row_renders(self):
        self.assertNotIn('class="label"', bt.filter_rows([m(themes=['arts'])]))


class TestEmptyCatalogue(unittest.TestCase):
    def test_no_tours_renders_no_chips_at_all(self):
        self.assertEqual(bt.filter_rows([]).strip(), '')



class TestBuiltPage(unittest.TestCase):
    """The invariant this whole change exists for, asserted on the real page:
    every chip filters something, and every card is reachable by a chip."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, 'tours.html'), encoding='utf-8') as f:
            cls.html = f.read()

    def cards(self, attr):
        found = set()
        for tag in re.findall(r'<a class="tcard".*?>', self.html, re.S):
            v = re.search(rf'data-{attr}="([^"]*)"', tag)
            if v and v.group(1):
                found.update(v.group(1).split())
        return found

    def test_the_filter_region_is_generated_not_hand_written(self):
        self.assertIn('<!-- CMS:tours-filters:start -->', self.html)
        self.assertIn('<!-- CMS:tours-filters:end -->', self.html)

    def test_every_theme_chip_matches_at_least_one_card(self):
        self.assertLessEqual(set(chips(self.html, 'theme')), self.cards('themes'))

    def test_every_theme_on_a_card_has_a_chip(self):
        themes = self.cards('themes')
        if len(themes) > 1:
            self.assertEqual(set(chips(self.html, 'theme')), themes)

    def test_every_area_chip_matches_at_least_one_card(self):
        areas = set(chips(self.html, 'area')) - {'all'}
        self.assertLessEqual(areas, self.cards('area'))

    def test_no_retired_theme_survives_on_the_page(self):
        # 'local' has no Bokun source; 'temples' was reinstated once
        # PILGRIMAGE_OR_RELIGION turned up in the vocabulary.
        self.assertNotIn('data-theme="local"', self.html)
if __name__ == '__main__':
    unittest.main()
