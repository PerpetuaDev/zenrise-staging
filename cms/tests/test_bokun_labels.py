# cms/tests/test_bokun_labels.py
import unittest

from cms import bokun_labels

# The six values verified live on product 1273194 -- see the task-18 brief.
# Map ONLY these; do not add speculative entries ahead of what the client's
# account is confirmed to use.
KNOWN = {
    'BUS_FARE': ('Bus fare', 'バス運賃'),
    'PARKING_FEES': ('Parking fees', '駐車料金'),
    'FOOD_AND_DRINKS': ('Food & drinks', '飲食'),
    'ENTRY_OR_ADMISSION_FEE': ('Entry & admission fees', '拝観料・入場料'),
    'GOODS_AND_SERVICES_TAX': ('Tax', '消費税'),
    'PUBLIC_TRANSPORTATION_NEARBY': ('Public transport nearby', '公共交通機関が近い'),
}


class TestLabel(unittest.TestCase):
    def test_every_verified_value_is_mapped_to_its_suggested_wording(self):
        for value, want in KNOWN.items():
            self.assertEqual(bokun_labels.label(value), want, value)

    def test_an_unmapped_value_returns_none(self):
        self.assertIsNone(bokun_labels.label('SOME_NEW_ENUM_VALUE'))

    def test_no_speculative_entries_beyond_the_verified_six(self):
        self.assertEqual(set(bokun_labels._LABELS), set(KNOWN))

    def test_none_input_returns_none(self):
        self.assertIsNone(bokun_labels.label(None))


if __name__ == '__main__':
    unittest.main()
