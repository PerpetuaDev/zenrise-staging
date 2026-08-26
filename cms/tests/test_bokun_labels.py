# cms/tests/test_bokun_labels.py
import unittest

from cms import bokun_labels

# Bokun's two closed vocabularies in full, captured on 2026-08-26 by ticking
# every box on one product and reading the API back -- Bokun exposes no
# reference endpoint for them. These are OBSERVED constants, not inferred from
# the panel's display labels: that distinction matters, because deriving them
# from the labels got all 12 inclusions right but only 6 of the 10 traveller
# values (STROLLER_OR_PRAM_ACCESSIBLE, LIMITED_MOBILITY_ACCESSIBLE,
# LIMITED_SIGHT_ACCESSIBLE and ANIMALS_OR_PETS_ALLOWED would all have been
# wrong). Anything outside this set must stay unmapped so the build warns.
INCLUSIONS = {
    'BUS_FARE', 'DEPARTURE_TAX', 'ENTRY_OR_ADMISSION_FEE', 'ENTRY_TAX',
    'FOOD_AND_DRINKS', 'FUEL_SURCHARGE', 'GOODS_AND_SERVICES_TAX',
    'LANDING_AND_FACILITY_FEES', 'NATIONAL_PARK_ENTRANCE_FEE', 'PARKING_FEES',
    'TIP_OR_GRATUITY', 'WIFI',
}
KNOW_BEFORE = {
    'ANIMALS_OR_PETS_ALLOWED', 'DRESS_CODE', 'INFANTS_MUST_SIT_ON_LAPS',
    'INFANT_SEATS_AVAILABLE', 'LIMITED_MOBILITY_ACCESSIBLE',
    'LIMITED_SIGHT_ACCESSIBLE', 'PASSPORT_REQUIRED',
    'PUBLIC_TRANSPORTATION_NEARBY', 'STROLLER_OR_PRAM_ACCESSIBLE',
    'WHEELCHAIR_ACCESSIBLE',
}
CONFIRMED = INCLUSIONS | KNOW_BEFORE


class TestLabel(unittest.TestCase):
    def test_every_confirmed_value_has_both_languages(self):
        for value in sorted(CONFIRMED):
            got = bokun_labels.label(value)
            self.assertIsNotNone(got, value)
            en, ja = got
            self.assertTrue(en.strip(), value)
            self.assertTrue(ja.strip(), value)
            # the label must be wording, never the constant leaking through
            self.assertNotEqual(en, value)
            self.assertNotIn('_', en)

    def test_japanese_is_actually_japanese_where_it_should_be(self):
        # Wi-Fi is a legitimate exception: it is written in latin in Japanese.
        latin_ok = {'WIFI'}
        cjk = lambda s: any('぀' <= ch <= 'ヿ' or '一' <= ch <= '鿿'
                            for ch in s)
        for value in sorted(CONFIRMED - latin_ok):
            self.assertTrue(cjk(bokun_labels.label(value)[1]), value)

    def test_no_entries_beyond_the_confirmed_vocabularies(self):
        self.assertEqual(set(bokun_labels._LABELS), CONFIRMED)

    def test_the_two_vocabularies_are_kept_separate(self):
        self.assertEqual(set(bokun_labels._INCLUSIONS), INCLUSIONS)
        self.assertEqual(set(bokun_labels._KNOW_BEFORE), KNOW_BEFORE)

    def test_an_unmapped_value_returns_none(self):
        self.assertIsNone(bokun_labels.label('SOME_NEW_ENUM_VALUE'))

    def test_none_input_returns_none(self):
        self.assertIsNone(bokun_labels.label(None))


if __name__ == '__main__':
    unittest.main()
