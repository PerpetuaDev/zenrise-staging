# cms/tests/test_tours_slug.py
import os
import tempfile
import unittest

from cms import tours_slug

# The four live slugs. Changing any of these breaks a published URL.
SEEDED = {
    '1273194': 'zen-journey',
    '1273232': 'ikebana-ichigo-ichie',
    '1273235': 'candle-making',
    '1275339': 'swordsmithing',
}


class TestDerive(unittest.TestCase):
    def test_reproduces_the_hand_picked_slugs(self):
        for title, want in [
            ('The Zen Journey', 'zen-journey'),
            ('Ikebana Experience , “Ichigo Ichie”-KAMAKURA', 'ikebana-ichigo-ichie'),
            ('A private Japanese candle-making experience in Kamakura.', 'candle-making'),
        ]:
            self.assertEqual(tours_slug.derive(title), want, title)

    def test_keeps_a_tour_name_that_follows_a_comma(self):
        # cutting at the comma would discard the distinctive part, and one real
        # title carries a stray comma from a typo
        self.assertEqual(tours_slug.derive('Swordsmithing, “The Smith’s Flame”'),
                         'swordsmithing-smiths-flame')

    def test_only_drops_a_place_when_it_trails(self):
        # dropping place names anywhere turned this into "harbour"
        self.assertEqual(tours_slug.derive('Yokohama Harbour, After Dark'),
                         'yokohama-harbour-after-dark')

    def test_drops_repeated_trailing_places(self):
        self.assertEqual(tours_slug.derive('Zazen Morning in Kamakura Tokyo'),
                         'zazen-morning')

    def test_japanese_only_title_yields_nothing(self):
        for t in ('禅の旅', '横浜ナイトウォーク', '', None):
            self.assertEqual(tours_slug.derive(t), '')

    def test_mixed_script_still_yields_something(self):
        # exactly why an empty slug cannot detect a missing English translation
        self.assertEqual(tours_slug.derive('ZENの旅'), 'zen')
        self.assertEqual(tours_slug.derive('鎌倉ZEN散歩'), 'zen')

    def test_a_title_of_only_filler_keeps_its_words(self):
        self.assertEqual(tours_slug.derive('The Tour'), 'the-tour')

    def test_caps_at_four_words(self):
        self.assertEqual(tours_slug.derive('One Two Three Four Five Six'),
                         'one-two-three-four')

    def test_slugify_strips_punctuation_and_accents(self):
        self.assertEqual(tours_slug.slugify('Wa-Rōsoku づくり'), 'wa-rosoku')
        self.assertEqual(tours_slug.slugify("Smith’s  Flame!"), 'smiths-flame')


class TestResolve(unittest.TestCase):
    def test_config_override_wins_over_everything(self):
        self.assertEqual(
            tours_slug.resolve('1273194', 'The Zen Journey', '禅の旅',
                               ['en', 'JA_JP'], SEEDED, override='custom'),
            ('custom', 'override'))

    def test_registry_wins_over_derivation(self):
        # a retitled tour keeps its published URL
        self.assertEqual(
            tours_slug.resolve('1273194', 'A Completely New Title', '禅の旅',
                               ['en', 'JA_JP'], SEEDED),
            ('zen-journey', 'registry'))

    def test_derives_for_a_new_translated_tour(self):
        self.assertEqual(
            tours_slug.resolve('999', 'Yokohama Harbour, After Dark',
                               '横浜、夜の港をあるく', ['en', 'JA_JP'], SEEDED),
            ('yokohama-harbour-after-dark', 'derived'))

    def test_refuses_when_there_is_no_english_language_slot(self):
        slug, why = tours_slug.resolve('999', 'Some English Title', '日本語タイトル',
                                       ['JA_JP'], SEEDED)
        self.assertEqual(slug, '')
        self.assertIn('language', why.lower())

    def test_refuses_when_the_slot_exists_but_is_unfilled(self):
        # both languages return the base content, so the titles match
        slug, why = tours_slug.resolve('999', 'Same Title', 'Same Title',
                                       ['en', 'JA_JP'], SEEDED)
        self.assertEqual(slug, '')
        self.assertIn('translat', why.lower())

    def test_refuses_when_the_english_title_yields_no_slug(self):
        slug, why = tours_slug.resolve('999', '禅の旅', '別の日本語', ['en', 'JA_JP'], SEEDED)
        self.assertEqual(slug, '')
        self.assertIn('usable', why.lower())

    def test_a_known_slug_is_returned_even_when_untranslated(self):
        # Ikebana's real case: no en slot, but its slug is already settled
        self.assertEqual(
            tours_slug.resolve('1273232', 'Ikebana', 'Ikebana', ['JA_JP'], SEEDED),
            ('ikebana-ichigo-ichie', 'registry'))

    def test_every_live_slug_survives_resolution_untouched(self):
        for pid, want in SEEDED.items():
            slug, why = tours_slug.resolve(pid, 'anything', 'anything', [], SEEDED)
            self.assertEqual(slug, want, pid)
            self.assertEqual(why, 'registry')

    def test_collision_gets_a_numeric_suffix(self):
        reg = {'111': 'zen-morning'}
        slug, _ = tours_slug.resolve('222', 'Zen Morning', '禅の朝',
                                     ['en', 'JA_JP'], reg)
        self.assertEqual(slug, 'zen-morning-2')

    def test_collision_skips_past_several(self):
        reg = {'111': 'zen-morning', '112': 'zen-morning-2'}
        slug, _ = tours_slug.resolve('222', 'Zen Morning', '禅の朝',
                                     ['en', 'JA_JP'], reg)
        self.assertEqual(slug, 'zen-morning-3')

    def test_a_tour_does_not_collide_with_its_own_entry(self):
        reg = {'999': 'zen-morning'}
        slug, why = tours_slug.resolve('999', 'Zen Morning', '禅の朝',
                                       ['en', 'JA_JP'], reg)
        self.assertEqual((slug, why), ('zen-morning', 'registry'))

    def test_int_and_str_ids_resolve_alike(self):
        self.assertEqual(tours_slug.resolve(1273194, 'x', 'y', [], SEEDED)[0],
                         'zen-journey')


class TestRegistryFile(unittest.TestCase):
    def test_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'r.json')
            tours_slug.save_registry(p, {'1': 'a-slug'})
            self.assertEqual(tours_slug.load_registry(p), {'1': 'a-slug'})

    def test_missing_registry_loads_empty(self):
        self.assertEqual(tours_slug.load_registry('/nonexistent/r.json'), {})

    def test_the_committed_registry_holds_the_live_slugs(self):
        self.assertEqual(tours_slug.load_registry(), SEEDED)


if __name__ == '__main__':
    unittest.main()
