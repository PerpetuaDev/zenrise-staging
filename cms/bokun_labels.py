"""Label map for Bokun's predefined, closed enum vocabularies.

`inclusions` and `knowBeforeYouGoItems` are lists of SCREAMING_SNAKE API
constants, not free text -- Bokun's own booking widget maps them to wording
internally, but the API hands back only the constant. They never localise
(`ja_differs=False`): they are our wording to supply in both languages, once,
for good, not Bokun content.

The full vocabularies were captured on 2026-08-26 by ticking every box on one
product and reading the API back, because Bokun exposes no reference endpoint
for them -- every candidate returned 404, and OCTO does not describe them
either. So these constants are observed, not inferred. That mattered: deriving
them from the panel's display labels got all 12 inclusions right but only 6 of
10 traveller-information values. The four that would have been wrong are noted
inline below.

An unmapped value must surface as a build warning (see bokun_source), never as
a raw constant on the page.

The Japanese is drafted by Claude and awaits the user's review.
"""

# ── inclusions ─────────────────────────────────────────────────────────────
# Bokun's "Inclusions checklist". All 12 constants confirmed live.
_INCLUSIONS = {
    'BUS_FARE': ('Bus fare', 'バス運賃'),
    'DEPARTURE_TAX': ('Departure tax', '出国税'),
    'ENTRY_OR_ADMISSION_FEE': ('Entry & admission fees', '拝観料・入場料'),
    'ENTRY_TAX': ('Entry tax', '入国税'),
    'FOOD_AND_DRINKS': ('Food & drinks', '飲食'),
    'FUEL_SURCHARGE': ('Fuel surcharge', '燃油サーチャージ'),
    'GOODS_AND_SERVICES_TAX': ('Tax', '消費税'),
    'LANDING_AND_FACILITY_FEES': ('Landing & facility fees', '着陸料・施設利用料'),
    'NATIONAL_PARK_ENTRANCE_FEE': ('National park entrance fee', '国立公園入園料'),
    'PARKING_FEES': ('Parking fees', '駐車料金'),
    'TIP_OR_GRATUITY': ('Tip or gratuity', 'チップ'),
    'WIFI': ('WiFi', 'Wi-Fi'),
}

# ── know before you go ─────────────────────────────────────────────────────
# Bokun's "Traveller information" checklist. All 10 constants confirmed live.
_KNOW_BEFORE = {
    # The constant reads broader than the panel's label, but per the user the
    # intent is unambiguous: assistance animals for disabled travellers, which
    # is what Bokun's panel calls it. 補助犬 is the term Japanese law uses for
    # service dogs -- guide, mobility-assistance and hearing dogs alike -- so it
    # carries the meaning precisely, where 動物・ペット would not.
    'ANIMALS_OR_PETS_ALLOWED': ('Service animals allowed', '補助犬同伴可'),
    'DRESS_CODE': ('Dress code applies', '服装の指定あり'),
    'INFANTS_MUST_SIT_ON_LAPS': ('Infants sit on your lap', '幼児は膝の上'),
    'INFANT_SEATS_AVAILABLE': ('Infant seats available', 'ベビーシートあり'),
    # would have been mis-derived as LIMITED_MOBILITY_ACCESS
    'LIMITED_MOBILITY_ACCESSIBLE': ('Accessible with limited mobility',
                                    '歩行に不安のある方に対応'),
    # would have been mis-derived as LIMITED_EYESIGHT_ACCESSIBLE
    'LIMITED_SIGHT_ACCESSIBLE': ('Accessible with limited sight',
                                 '視覚に障がいのある方に対応'),
    'PASSPORT_REQUIRED': ('Passport required', 'パスポート必須'),
    'PUBLIC_TRANSPORTATION_NEARBY': ('Public transport nearby', '公共交通機関が近い'),
    # would have been mis-derived as STROLLER_ACCESSIBLE
    'STROLLER_OR_PRAM_ACCESSIBLE': ('Stroller or pram accessible', 'ベビーカー可'),
    'WHEELCHAIR_ACCESSIBLE': ('Wheelchair accessible', '車椅子可'),
}

_LABELS = {**_INCLUSIONS, **_KNOW_BEFORE}


def label(value):
    """(en, ja) for a known enum value, or None when it isn't in the map."""
    return _LABELS.get(value)
