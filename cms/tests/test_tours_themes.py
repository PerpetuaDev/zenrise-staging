# cms/tests/test_tours_themes.py
import json, os, unittest

from cms import bokun_source, tours_themes

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
IKEBANA, CANDLE, ZEN = 1273232, 1273235, 1273194


def activity(pid, **fields):
    with open(os.path.join(DATA, f'activity-{pid}-EN.json')) as f:
        return dict(json.load(f), **fields)


def themes_of(pid, entry, **fields):
    a = activity(pid, **fields)
    rec, warnings, _ = bokun_source.to_record(a, a, [], [], entry, {})
    return rec['themes'], warnings


class TestCategoryMapping(unittest.TestCase):
    def test_pilgrimage_maps_to_temples(self):
        # The most important theme for a Kamakura operator, and the one the
        # first vocabulary capture missed entirely.
        slugs, _ = tours_themes.from_categories(['PILGRIMAGE_OR_RELIGION'])
        self.assertEqual(slugs, ['temples'])

    def test_walking_tour_maps_to_walking(self):
        slugs, _ = tours_themes.from_categories(['WALKING_TOUR'])
        self.assertEqual(slugs, ['walking'])

    def test_nature_maps_to_nature(self):
        slugs, _ = tours_themes.from_categories(['NATURE'])
        self.assertEqual(slugs, ['nature'])

    def test_hiking_and_birdwatching_also_read_as_nature(self):
        slugs, _ = tours_themes.from_categories(['HIKING', 'BIRDWATCHING'])
        self.assertEqual(slugs, ['nature'])

    def test_both_arts_categories_map_to_the_one_arts_slug(self):
        slugs, _ = tours_themes.from_categories(
            ['ARTS_AND_CULTURE', 'CLASSES_AND_WORKSHOPS'])
        self.assertEqual(slugs, ['arts'])

    def test_three_categories_fold_into_culture(self):
        slugs, _ = tours_themes.from_categories(
            ['CULTURAL_AND_THEME_TOURS', 'EDUCATIONAL_TOUR', 'FESTIVAL'])
        self.assertEqual(slugs, ['culture'])

    def test_culinary_maps_to_food(self):
        slugs, _ = tours_themes.from_categories(['CULINARY'])
        self.assertEqual(slugs, ['food'])

    def test_both_bike_categories_map_to_cycling(self):
        slugs, _ = tours_themes.from_categories(['BIKE_TOUR', 'EBIKE_TOUR'])
        self.assertEqual(slugs, ['cycling'])

    def test_slugs_come_back_in_canonical_order_not_bokun_order(self):
        # Bokun lists categories in its own order; the chip row must not
        # reshuffle when the client edits an unrelated tag.
        slugs, _ = tours_themes.from_categories(
            ['WALKING_TOUR', 'PILGRIMAGE_OR_RELIGION', 'CULINARY',
             'CULTURAL_AND_THEME_TOURS'])
        self.assertEqual(slugs, ['temples', 'culture', 'food', 'walking'])

    def test_zen_journeys_real_tagging(self):
        # Exactly what the client has on the tour today.
        slugs, warnings = tours_themes.from_categories([
            'CULTURAL_AND_THEME_TOURS', 'LUXURY_AND_SPECIAL_OCCASIONS', 'NATURE',
            'PHOTOGRAPHY', 'PILGRIMAGE_OR_RELIGION', 'SIGHTSEEING',
            'SIGHTSEEING_ATTRACTION', 'WALKING_TOUR'])
        self.assertEqual(slugs, ['temples', 'culture', 'walking', 'nature'])
        self.assertEqual(warnings, [])


class TestNoise(unittest.TestCase):
    def test_shelf_categories_yield_no_theme_and_no_warning(self):
        # SIGHTSEEING alone is on six of the eleven products: mapping it would
        # put most of the catalogue in one chip and separate nothing.
        slugs, warnings = tours_themes.from_categories(
            ['SIGHTSEEING', 'SIGHTSEEING_ATTRACTION', 'DAY_TRIPS_AND_EXCURSIONS',
             'LUXURY_AND_SPECIAL_OCCASIONS', 'HOLIDAY_AND_SEASONAL_TOURS',
             'CITY_BREAK', 'CITY_TOURS', 'SHORE_EXCURSIONS'])
        self.assertEqual(slugs, [])
        self.assertEqual(warnings, [])

    def test_transport_format_categories_are_ignored(self):
        slugs, warnings = tours_themes.from_categories(
            ['BUS_TOUR', 'HOP_ON_HOP_OFF_TOUR', 'AIR_OR_HELICOPTER_TOUR',
             'CLASSIC_CAR_TOURS', 'HORSE_CARRIAGE_RIDE', 'AIRPORT_LOUNGE'])
        self.assertEqual((slugs, warnings), ([], []))

    def test_off_brand_activities_are_ignored(self):
        slugs, warnings = tours_themes.from_categories(
            ['GOLF', 'HUNTING', 'JET_SKI_TOUR', 'ADRENALINE_AND_EXTREME',
             'ICE_CLIMBING', 'ESCAPE_GAME', 'SHOPPING', 'THEME_PARKS'])
        self.assertEqual((slugs, warnings), ([], []))

    def test_photography_is_ignored_deliberately(self):
        # Zen Journey -- a seated-meditation temple walk -- is tagged with it,
        # so it attaches to anything scenic rather than to photography tours.
        slugs, warnings = tours_themes.from_categories(['PHOTOGRAPHY'])
        self.assertEqual((slugs, warnings), ([], []))

    def test_unknown_category_warns_and_names_the_value(self):
        # The vocabulary is not enumerable and the bulk capture proved
        # incomplete, so an unmapped value must announce itself by name.
        slugs, warnings = tours_themes.from_categories(['SOMETHING_NEW'])
        self.assertEqual(slugs, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn('SOMETHING_NEW', warnings[0])


class TestPrecedence(unittest.TestCase):
    """Bokun when it has something to say, tours-config.json when it does not."""

    ENTRY = {'slug': 'x', 'number': '01', 'area': 'Kamakura', 'jaReviewed': False}

    def test_bokun_categories_win_over_the_config_seed(self):
        themes, _ = themes_of(ZEN, dict(self.ENTRY, themes=['arts']))
        self.assertEqual(themes, ['culture', 'walking'])

    def test_config_seeds_a_tour_bokun_has_not_tagged(self):
        # candle-making is live with an empty activityCategories; it must keep
        # its chip rather than silently drop out of theme filtering.
        themes, _ = themes_of(CANDLE, dict(self.ENTRY, themes=['arts']))
        self.assertEqual(themes, ['arts'])

    def test_untagged_and_unseeded_tour_is_themeless_and_warns(self):
        themes, warnings = themes_of(CANDLE, dict(self.ENTRY))
        self.assertEqual(themes, [])
        self.assertTrue(any('no theme' in w for w in warnings), warnings)

    def test_a_themeless_tour_is_not_held_back(self):
        # Themes are editorial, not structural: a tour with none still belongs
        # on the site, just not under a chip.
        a = activity(CANDLE)
        rec, _, _ = bokun_source.to_record(a, a, [], [], dict(self.ENTRY), {})
        self.assertEqual(rec['id'], 'x')

    def test_ikebana_derives_arts_and_culture_from_bokun(self):
        themes, _ = themes_of(IKEBANA, dict(self.ENTRY))
        self.assertEqual(themes, ['culture', 'arts'])
