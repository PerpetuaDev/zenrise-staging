"""Label map for Bokun's predefined, closed enum vocabularies.

`inclusions` and `knowBeforeYouGoItems` are lists of SCREAMING_SNAKE API
constants, not free text -- Bokun's own booking widget maps them to wording
internally, but the API hands back only the constant. They never localise
(`ja_differs=False`): they are our wording to supply in both languages, once,
for good, not Bokun content gated by jaReviewed. See task 18 brief.

Map ONLY values actually seen live on the client's account (verified on
product 1273194). Do not add speculative entries ahead of what Bokun's
account is confirmed to use -- an unmapped value must surface as a build
warning (see bokun_source.to_record), never as a raw constant on the page.
"""

_LABELS = {
    'BUS_FARE': ('Bus fare', 'バス運賃'),
    'PARKING_FEES': ('Parking fees', '駐車料金'),
    'FOOD_AND_DRINKS': ('Food & drinks', '飲食'),
    'ENTRY_OR_ADMISSION_FEE': ('Entry & admission fees', '拝観料・入場料'),
    'GOODS_AND_SERVICES_TAX': ('Tax', '消費税'),
    'PUBLIC_TRANSPORTATION_NEARBY': ('Public transport nearby', '公共交通機関が近い'),
}


def label(value):
    """(en, ja) for a known enum value, or None when it isn't in the map."""
    return _LABELS.get(value)
