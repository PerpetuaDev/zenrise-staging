"""The tours filter vocabulary: Bokun's activityCategories -> our theme slugs.

Bokun is the source of truth for what a tour is about, so the site's themes are
narrowed to what Bokun's taxonomy can actually express. Two consequences worth
knowing before editing this file:

* Bokun's vocabulary is OTA-shaped and the client tags generously -- one product
  carries eleven categories. Mapping everything would put most of the catalogue
  in every chip, so the values that carry no editorial signal are ignored
  explicitly rather than by omission.
* There is no endpoint that enumerates the vocabulary (four plausible paths all
  404). An unmapped value is therefore how a new one announces itself: it is
  reported by name so the hourly build surfaces it, instead of vanishing.

`ORDER` is also the chip order on tours.html. It keeps the design handoff's
relative order for the themes that survived the narrowing, with `arts` -- which
had no chip at all before -- appended.
"""

ORDER = ['temples', 'culture', 'arts', 'food', 'walking', 'nature']

# Many Bokun values fold into one editorial chip. Mapping generously costs
# nothing: a chip only renders when a published tour actually carries it, so an
# unused mapping is invisible on the site.
CATEGORY_THEME = {
    'PILGRIMAGE_OR_RELIGION': 'temples',

    'CULTURAL_AND_THEME_TOURS': 'culture',
    'EDUCATIONAL_TOUR': 'culture',
    'FESTIVAL': 'culture',

    'ARTS_AND_CULTURE': 'arts',
    'CLASSES_AND_WORKSHOPS': 'arts',

    'CULINARY': 'food',

    'WALKING_TOUR': 'walking',

    'NATURE': 'nature',
    'HIKING': 'nature',
    'BIRDWATCHING': 'nature',
}

# Real values that describe an OTA shelf, a mode of transport, or an activity
# outside what Zenrise sells. Ignored explicitly rather than by omission, so
# that anything NOT listed here is genuinely new and gets reported.
IGNORED = {
    # the shelf a tour sits on, not what it is
    'SIGHTSEEING', 'SIGHTSEEING_ATTRACTION', 'DAY_TRIPS_AND_EXCURSIONS',
    'HOLIDAY_AND_SEASONAL_TOURS', 'LUXURY_AND_SPECIAL_OCCASIONS', 'CITY_BREAK',
    'CITY_TOURS', 'SHORE_EXCURSIONS', 'ADVENTURE',
    # how you travel, not what you see
    'BUS_TOUR', 'BUS_OR_MINIVAN_TOUR', 'HOP_ON_HOP_OFF_TOUR', 'CLASSIC_CAR_TOURS',
    'AIR_OR_HELICOPTER_TOUR', 'AIRPORT_LOUNGE', 'HORSE_CARRIAGE_RIDE',
    # off-brand activities
    'ADRENALINE_AND_EXTREME', 'ATV_OR_QUAD_TOUR', 'CLIMBING', 'ICE_CLIMBING',
    'GLACIER_HIKING', 'CAVING', 'HUNTING', 'FISHING', 'GOLF', 'HORSEBACK_RIDING',
    'JET_SKI_TOUR', 'CANOEING', 'DIVING', 'DOLPHIN_OR_WHALEWATCHING',
    'AMUSEMENT_PARK', 'THEME_PARKS', 'ESCAPE_GAME', 'SHOPPING',
    'BIKE_TOUR', 'EBIKE_TOUR',
    # Deliberate: Zen Journey -- a seated-meditation temple walk -- carries it,
    # so it marks anything scenic rather than an actual photography tour. Move
    # it into CATEGORY_THEME if a real one ever appears.
    'PHOTOGRAPHY',
}


def from_categories(categories):
    """Map Bokun activityCategories onto theme slugs. Returns (slugs, warnings)."""
    slugs, warnings = set(), []
    for c in categories or []:
        if c in IGNORED:
            continue
        slug = CATEGORY_THEME.get(c)
        if slug:
            slugs.add(slug)
        else:
            warnings.append(
                f'unknown Bokun category {c!r}: it maps to no theme and to no '
                f'chip. Add it to CATEGORY_THEME or IGNORED in cms/tours_themes.py.')
    return [s for s in ORDER if s in slugs], warnings


# The English chip label, which is also the inline fallback in the markup before
# lang.js swaps it. Kept beside the vocabulary so a new theme is one edit here.
LABEL_EN = {
    'temples': 'Temples &amp; Shrines',
    'culture': 'Culture',
    'arts': 'Arts &amp; Craft',
    'food': 'Food &amp; Drink',
    'walking': 'Walking',
    'nature': 'Nature &amp; Views',
}

I18N_KEY = {s: f'tours_theme_{s}' for s in ORDER}
