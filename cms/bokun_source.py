"""Fetch the Zenrise-tier products from Bokun as fixture-shaped records.

Records use exactly the keys of cms/tours-fixture.json entries so that
build-tours.py's tour_model() and every downstream renderer stay unchanged.
Four keys are added: bokunId, widgets, priceRows, jaReviewed.
"""
from datetime import datetime, timedelta, timezone

from . import bokun_price, bokun_text, tours_config

PAIR_FIELDS = ('title', 'sub', 'lede', 'coverCaption')

# Bokun field -> record field for the four fixed chip groups (task 17), minus
# 'included' which is handled separately below because it alone carries a
# description-parsing fallback. These are structured fields (each holding a
# <li> list), not open-ended vocabulary, so mapping them once gives every
# future tour chips with no developer involvement. 'notAllowed'/'notSuitable'
# are retired: no Bokun field ever fed them, so they could only ever render
# empty.
CHIP_FIELDS = (('excluded', 'notIncluded'), ('requirements', 'bring'), ('attention', 'know'))


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


def to_record(activity, activity_ja, availability, availability_ja, entry, corr):
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
    reviewed = bool(entry.get('jaReviewed'))

    # The Japanese description is only trusted (and only fetched into the
    # correction-usage ledger) once a tour is jaReviewed -- same gate as the
    # Japanese lede a few lines below.
    parsed_ja_included = []
    if reviewed:
        raw_texts.append((activity_ja or {}).get('description') or '')
        parsed_ja, sw_ja = bokun_text.sections(
            (activity_ja or {}).get('description'), corr, entry.get('chipsHeading'))
        warnings.extend(sw_ja)
        parsed_ja_included = parsed_ja['included']

    def chip_items(raw):
        return [x for x in (cl(li) for li in bokun_text.list_items(raw)) if x]

    def chip_group(bokun_field, desc_fallback_en=(), desc_fallback_ja=()):
        """(en, ja) newline-joined chip text for one of the four fixed groups.

        Fallback order, and it matters (task 17): <li> items from the field
        itself; then, for the Included group only, the existing
        description-parsing (Ikebana's included field is one prose sentence
        with no list, while its description still carries a 6-item list);
        then the field's own plain text as a single item. A group with
        nothing at all stays empty -- chips_section already renders that as
        no group, and must keep doing so.
        """
        en_items = chip_items(activity.get(bokun_field))
        if not en_items and desc_fallback_en:
            en_items = list(desc_fallback_en)
        if not en_items:
            plain = cl(activity.get(bokun_field))
            en_items = [plain] if plain else []
        en_joined = '\n'.join(en_items)

        if reviewed:
            ja_items = chip_items((activity_ja or {}).get(bokun_field))
            if not ja_items and desc_fallback_ja:
                ja_items = list(desc_fallback_ja)
            if not ja_items:
                plain_ja = cl((activity_ja or {}).get(bokun_field))
                ja_items = [plain_ja] if plain_ja else []
            ja_joined = '\n'.join(ja_items) or en_joined
        else:
            # Bokun's Japanese chip content is no more trusted, pre-review,
            # than any other Japanese field -- mirror English exactly as
            # title/sub/lede do above.
            ja_joined = en_joined
        return en_joined, ja_joined

    chips = {'included': chip_group(
        'included', desc_fallback_en=parsed['included'], desc_fallback_ja=parsed_ja_included)}
    for bokun_field, rec_field in CHIP_FIELDS:
        chips[rec_field] = chip_group(bokun_field)

    # agendaItems genuinely localise in Bokun (verified live on product
    # 1273194), but only once a tour is jaReviewed do we trust that Japanese
    # enough to show it — same gate as title/sub/lede below. Steps are paired
    # by index; a Japanese list that is shorter (or absent) just leaves the
    # remaining/ungated stops mirroring English, same as an untranslated stop.
    route = []
    agenda_ja = (activity_ja or {}).get('agendaItems') or []
    for idx, item in enumerate(activity.get('agendaItems') or []):
        title_en = cl(item.get('title'))
        body_en = cl(item.get('body'))
        item_ja = agenda_ja[idx] if reviewed and idx < len(agenda_ja) else None
        title_ja = cl(item_ja.get('title')) if item_ja else title_en
        body_ja = cl(item_ja.get('body')) if item_ja else body_en
        route.append({
            'title': title_en, 'body': body_en,
            'titleJa': title_ja or title_en, 'bodyJa': body_ja or body_en,
        })

    photos = activity.get('photos') or []
    cover = (photos[0].get('originalUrl') if photos else '') or ''
    cover_cap = cl(photos[0].get('alternateText')) if photos else ''

    # Rate titles and pricing-category titles are both localised the same
    # way title/sub/lede/route are above: only once a tour is jaReviewed do
    # we trust Bokun's Japanese enough to show it. An unreviewed tour (or
    # one where the Japanese availability call failed/came back empty, see
    # fetch_records) simply gets no category_ja/rate_title_ja on its rows,
    # and bokun_price.format_full falls back to the hand-written _CAT_JA
    # map / the English rate title exactly as it always has.
    pricing_categories_ja = (activity_ja or {}).get('pricingCategories') or [] if reviewed else []
    rows = bokun_price.rows(
        availability, activity.get('pricingCategories') or [],
        pricing_categories_ja=pricing_categories_ja,
        availability_ja=availability_ja if reviewed else None)
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
        'includedEn': chips['included'][0], 'includedJa': chips['included'][1],
        'notIncludedEn': chips['notIncluded'][0], 'notIncludedJa': chips['notIncluded'][1],
        'bringEn': chips['bring'][0], 'bringJa': chips['bring'][1],
        'knowEn': chips['know'][0], 'knowJa': chips['know'][1],
    }

    en_values = {'title': title, 'sub': sub, 'lede': lede, 'coverCaption': cover_cap}
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
            f'/activity.json/{pid}/availabilities?start={today}&end={end}&lang=EN')
        # A label is not worth failing a build over: if the Japanese
        # availability call itself raises, or comes back as None (as
        # opposed to a well-formed empty list, which just means no slots in
        # this window — not a failure), fall back to English rate titles
        # and carry on, with a warning so the gap is visible.
        availability_ja = None
        try:
            availability_ja = client.get(
                f'/activity.json/{pid}/availabilities?start={today}&end={end}&lang=ja')
        except Exception as e:
            warnings.append(
                f'[{entry["slug"]}] Japanese availability request failed '
                f'({e}); price labels fall back to English for this tour.')
        else:
            if availability_ja is None:
                warnings.append(
                    f'[{entry["slug"]}] Japanese availability returned nothing; '
                    f'price labels fall back to English for this tour.')
        availability_ja = availability_ja or []
        rec, w, texts = to_record(activity, activity_ja, availability, availability_ja, entry, corr)
        records.append(rec)
        warnings += [f'[{rec["id"]}] {x}' for x in w]
        raw_texts += texts
    for stale in bokun_text.unused_corrections(raw_texts, corr):
        warnings.append(f'correction no longer matches any source text, safe to '
                        f'prune from tours-config.json: {stale!r}')
    return records, warnings
