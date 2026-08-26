"""Fetch the Zenrise-tier products from Bokun as fixture-shaped records.

Records use exactly the keys of cms/tours-fixture.json entries so that
build-tours.py's tour_model() and every downstream renderer stay unchanged.
Four keys are added: bokunId, widgets, priceRows, jaReviewed.
"""
from datetime import datetime, timedelta, timezone

from . import bokun_price, bokun_text, tours_config

PAIR_FIELDS = ('title', 'sub', 'lede', 'coverCaption',
               'included', 'notIncluded', 'notAllowed', 'notSuitable')


def _reject_ota(ids, denylist):
    """Defence in depth: never render an OTA-tier product, however its id was
    resolved. The allowlist/product-list already exclude them by construction;
    this catches the case where that exclusion was itself a mistake."""
    for i in ids:
        if i in denylist:
            raise tours_config.ConfigError(
                f'Bokun product {i} is on the OTA denylist and must never be '
                f'rendered on this site. Remove it from the product list or '
                f'allowlist before building.')


def catalogue(client, cfg):
    """Product list by name if it exists, otherwise the config allowlist."""
    denylist = set(tours_config.ota_denylist(cfg))
    wanted = (cfg.get('productListName') or '').strip().lower()
    if wanted:
        try:
            lists = client.get('/product-list.json/list') or []
        except Exception:
            lists = []
        for pl in lists:
            if (pl.get('title') or '').strip().lower() == wanted:
                ids = [int(it['activityId']) for it in (pl.get('items') or [])
                       if it.get('activityId')]
                if ids:
                    _reject_ota(ids, denylist)
                    return ids
    ids = tours_config.catalogue_ids(cfg)
    _reject_ota(ids, denylist)
    return ids


def _length_from_duration(duration_text):
    digits = ''.join(c for c in (duration_text or '') if c.isdigit() or c == ' ')
    first = digits.split()
    hours = int(first[0]) if first and first[0].isdigit() else 0
    return 'Full-day' if hours >= 5 else 'Half-day'


def to_record(activity, activity_ja, availability, entry, corr):
    warnings = []
    # Every raw string that is actually run through cl() (or, for the
    # description, through bokun_text.sections() below) is captured here, so
    # that unused_corrections() reports the truth: a correction that only
    # fixes damage in a route step or a photo caption must not be reported as
    # safe to prune.
    raw_texts = []

    def cl(value):
        raw_texts.append(value or '')
        text, w = bokun_text.clean(value, corr)
        warnings.extend(w)
        return text

    title = cl(activity.get('title'))
    sub = cl(activity.get('excerpt'))
    raw_texts.append(activity.get('description') or '')
    parsed, sw = bokun_text.sections(
        activity.get('description'), corr, entry.get('chipsHeading'))
    warnings.extend(sw)
    lede = ' '.join(parsed['lede'])
    included = '\n'.join(parsed['included'])
    reviewed = bool(entry.get('jaReviewed'))

    route = []
    for item in activity.get('agendaItems') or []:
        route.append({'title': cl(item.get('title')), 'body': cl(item.get('body'))})

    photos = activity.get('photos') or []
    cover = (photos[0].get('originalUrl') if photos else '') or ''
    cover_cap = cl(photos[0].get('alternateText')) if photos else ''

    rows = bokun_price.rows(availability, activity.get('pricingCategories') or [])
    fp = bokun_price.from_price(rows)

    rec = {
        'id': entry['slug'],
        'bokunId': int(activity['id']),
        'number': entry.get('number') or '',
        'area': entry.get('area') or (activity.get('googlePlace') or {}).get('city') or '',
        'length': entry.get('length') or _length_from_duration(activity.get('durationText')),
        'themes': entry.get('themes') or [],
        'cover': {'url': cover},
        'hoursEn': cl(activity.get('durationText')),
        'hoursJa': cl((activity_ja or {}).get('durationText')) or cl(activity.get('durationText')),
        'priceEn': bokun_price.format_from(fp, 'en'),
        'priceJa': bokun_price.format_from(fp, 'ja'),
        'priceRows': rows,
        'widgets': entry.get('widgets') or {},
        'jaReviewed': reviewed,
        'route': route,
    }

    en_values = {'title': title, 'sub': sub, 'lede': lede, 'coverCaption': cover_cap,
                 'included': included,
                 'notIncluded': '', 'notAllowed': '', 'notSuitable': ''}
    for field in PAIR_FIELDS:
        rec[field + 'En'] = en_values[field]
        if reviewed and field in ('title', 'sub', 'lede'):
            src = {'title': 'title', 'sub': 'excerpt', 'lede': 'description'}[field]
            rec[field + 'Ja'] = cl((activity_ja or {}).get(src)) or en_values[field]
        else:
            # Bokun holds no Japanese product copy. Mirroring English is the
            # honest fallback; raw machine translation must not reach the site.
            rec[field + 'Ja'] = en_values[field]
    return rec, warnings, raw_texts


def fetch_records(client, cfg):
    corr = tours_config.corrections(cfg)
    today = datetime.now(timezone.utc).date()
    # A year, not a quarter. Price is derived from availability, so a window
    # shorter than a tour's first bookable date silently reports it as unpriced:
    # Swordsmithing's first slot is 10 Nov 2026 and a 75-day window from 26 Aug
    # ended 9 Nov, one day short, so it was wrongly shown as "in preparation".
    end = today + timedelta(days=365)
    records, warnings, raw_texts = [], [], []
    for pid in catalogue(client, cfg):
        entry = tours_config.tour_entry(cfg, pid)
        activity = client.get(f'/activity.json/{pid}?lang=EN')
        activity_ja = client.get(f'/activity.json/{pid}?lang=ja')
        availability = client.get(
            f'/activity.json/{pid}/availabilities?start={today}&end={end}')
        rec, w, texts = to_record(activity, activity_ja, availability, entry, corr)
        records.append(rec)
        warnings += [f'[{rec["id"]}] {x}' for x in w]
        raw_texts += texts
    for stale in bokun_text.unused_corrections(raw_texts, corr):
        warnings.append(f'correction no longer matches any source text, safe to '
                        f'prune from tours-config.json: {stale!r}')
    return records, warnings
