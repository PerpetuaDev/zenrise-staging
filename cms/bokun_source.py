"""Fetch the Zenrise-tier products from Bokun as fixture-shaped records.

Records use exactly the keys of cms/tours-fixture.json entries so that
build-tours.py's tour_model() and every downstream renderer stay unchanged.
Four keys are added: bokunId, widgets, priceRows, jaReviewed.
"""
from datetime import datetime, timedelta, timezone

from . import bokun_labels, bokun_price, bokun_text, tours_config, tours_slug

PAIR_FIELDS = ('title', 'sub', 'lede', 'coverCaption')

# Bokun field -> record field for the four fixed PROSE groups (task 17,
# reclassified as prose rather than chips in task 18), minus 'included' which
# is handled separately below because it alone carries a description-parsing
# fallback. These are structured fields (each holding a <li> list) of full
# sentences, not short labels, so they render as prose. 'notAllowed'/
# 'notSuitable' are retired: no Bokun field ever fed them, so they could only
# ever render empty.
PROSE_FIELDS = (('excluded', 'notIncluded'), ('requirements', 'bring'), ('attention', 'know'))

# Bokun field -> record field for the two groups that also carry a closed,
# predefined enum vocabulary (task 18). Unlike PROSE_FIELDS above, these
# values are API constants (SCREAMING_SNAKE), looked up in bokun_labels.py,
# and rendered as real chips. 'excluded'/'requirements' have no enum
# counterpart in Bokun at all -- their groups stay prose-only.
ENUM_CHIP_FIELDS = (('inclusions', 'includedChips'), ('knowBeforeYouGoItems', 'knowChips'))


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


class Note(str):
    """An informational build-log line that is not a warning.

    Routine catalogue resolution is logged on every run, so printing it under a
    WARNING prefix trains the reader to ignore the prefix -- and a real warning
    then hides in the noise. Subclassing str keeps every existing consumer,
    including the tests' substring assertions, working unchanged.
    """


def catalogue(client, cfg, warnings=None):
    """Product list by name if it exists (gate 2, "Published"), otherwise the
    config allowlist.

    `/product-list.json/list` returns SUMMARIES only -- no membership -- so a
    matching list's membership has to be fetched separately from
    `/product-list.json/<id>`, whose `items` are shaped
    `{'activity': {'id': ..., 'title': ...}, 'productCategory': ...}`.

    An empty list is a real, deliberate "publish nothing" and is returned as
    such -- it must never be treated as "no list, fall back". Fallback only
    happens when no list of this name exists at all.

    `warnings`, if given, gets a human-readable note on how the catalogue was
    resolved (list membership, or the allowlist fallback) so a tour's absence
    is traceable from the build log alone (spec 3.1/3.2).
    """
    if warnings is None:
        warnings = []
    denylist = set(tours_config.ota_denylist(cfg))
    name = cfg.get('productListName') or 'Website'
    wanted = name.strip().lower()
    ids = None
    if wanted:
        try:
            lists = client.get('/product-list.json/list') or []
        except Exception:
            lists = []
        for pl in lists:
            if (pl.get('title') or '').strip().lower() == wanted:
                detail = client.get(f"/product-list.json/{pl['id']}") or {}
                ids = [int(it['activity']['id']) for it in (detail.get('items') or [])
                       if (it.get('activity') or {}).get('id')]
                break
    if ids is None:
        ids = tours_config.catalogue_ids(cfg)
        warnings.append(
            f'no product list named {name!r} found; falling back to the '
            f'config allowlist ({len(ids)} id(s)): {ids}.')
    else:
        warnings.append(Note(f'product list {name!r} has {len(ids)} member(s): {ids}.'))
        # A tour that silently vanishes is the failure mode this logging exists
        # to prevent, so name the tier products the list leaves out. The config
        # allowlist is the only "all known tier products" set available without
        # another round of API calls; it is a superset in practice because every
        # tour that has ever been published has an entry.
        try:
            known = tours_config.catalogue_ids(cfg)
        except tours_config.ConfigError:
            known = []
        for i in known:
            if i not in set(ids) and i not in denylist:
                warnings.append(
                    f'held back: Bokun product {i} is not a member of the '
                    f'{name!r} product list.')
    _reject_ota(ids, denylist)
    return ids


# Bokun carries NO per-rate duration: a rate has only id, title, description
# and minPerBooking, and the activity carries a single duration and a single
# start time. So a tour sold as both a half day and a full day says so in its
# rate titles and nowhere else -- reading them is the only zero-touch signal
# available. A config `length` still overrides, as it does for every other
# derived field.
_FULL_DAY = ('full day', 'full-day', 'fullday', '1\u65e5', '\u4e00\u65e5', '\u7d42\u65e5')
# "harf" is the client's own typo. It reached the live account once and was
# corrected, so it is cheap insurance rather than a hypothetical.
_HALF_DAY = ('half day', 'half-day', 'halfday',
             'harf day', 'harf-day', 'harfday', '\u534a\u65e5')


def _length_from_rates(rows):
    """'Full / Half-day', 'Full-day', 'Half-day', or '' when the rates say nothing.

    Both the English and Japanese rate titles are scanned, so this keeps working
    once the client translates rate names -- today they are identical.
    """
    titles = [str(r.get(k) or '').lower()
              for r in (rows or [])
              for k in ('rate_title', 'rate_title_ja')]
    full = any(any(m in t for m in _FULL_DAY) for t in titles)
    half = any(any(m in t for m in _HALF_DAY) for t in titles)
    if full and half:
        return 'Full / Half-day'
    if full:
        return 'Full-day'
    if half:
        return 'Half-day'
    return ''


def _length_from_duration(duration_text):
    digits = ''.join(c for c in (duration_text or '') if c.isdigit() or c == ' ')
    first = digits.split()
    hours = int(first[0]) if first and first[0].isdigit() else 0
    return 'Full-day' if hours >= 5 else 'Half-day'


def _trailing_place(en_title):
    """The single trailing place name a slug derivation would drop from this
    title (e.g. 'Kamakura' from '...-KAMAKURA'), title-cased, or '' if the
    title does not end in one of tours_slug.PLACES. Used as the second-choice
    source for `area` (spec 3.6) when googlePlace carries no city."""
    words = [w for w in tours_slug.slugify(en_title).split('-') if w]
    if len(words) > 1 and words[-1] in tours_slug.PLACES:
        return words[-1].title()
    return ''


def cdn_base(photo):
    """The Bokun image CDN base for a photo, or '' when it has no derivatives.

    Read off a named derivative rather than hardcoding imgcdn.bokun.tools, so a
    host change on Bokun's side follows automatically. Callers append their own
    ?w=&h= to request the size they actually display: the originals here are
    around 4000x2800, and were being served whole to a 430px card and a 760px
    hero, which is why those pages loaded slowly.
    """
    for d in (photo or {}).get('derived') or []:
        u = d.get('url') or ''
        if '?' in u:
            return u.split('?', 1)[0]
    return ''


def _agenda_photo(item):
    """(url, cdn_base) for an agenda item's key photo. Either may be ''.

    The URL is a named derivative as a safe default; the base lets the renderer
    ask for the exact size the thumbnail cell needs.
    """
    kp = item.get('keyPhoto') or {}
    derived = {d.get('name'): d.get('url')
               for d in (kp.get('derived') or []) if d.get('url')}
    url = ''
    for name in ('preview', 'large', 'thumbnail'):
        if derived.get(name):
            url = derived[name]
            break
    return (url or kp.get('originalUrl') or ''), cdn_base(kp)


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
    # Kept as a list as well as joined: the detail page renders the first
    # paragraph large and the rest smaller, breaking where Bokun's description
    # breaks. The joined form stays because the meta description and JSON-LD
    # want one continuous string.
    lede_paras = list(parsed['lede'])
    lede = ' '.join(parsed['lede'])
    reviewed = bool(entry.get('jaReviewed'))

    # The Japanese description is only trusted (and only fetched into the
    # correction-usage ledger) once a tour is jaReviewed -- same gate as the
    # Japanese lede a few lines below.
    parsed_ja_included = []
    parsed_ja_lede = []
    if reviewed:
        raw_texts.append((activity_ja or {}).get('description') or '')
        parsed_ja, sw_ja = bokun_text.sections(
            (activity_ja or {}).get('description'), corr, entry.get('chipsHeading'))
        warnings.extend(sw_ja)
        parsed_ja_included = parsed_ja['included']
        parsed_ja_lede = list(parsed_ja['lede'])

    def prose_items(raw):
        return [x for x in (cl(li) for li in bokun_text.list_items(raw)) if x]

    def prose_group(bokun_field, desc_fallback_en=(), desc_fallback_ja=()):
        """(en, ja) newline-joined PROSE text for one of the four fixed groups.

        Fallback order, and it matters (task 17): <li> items from the field
        itself; then, for the Included group only, the existing
        description-parsing (Ikebana's included field is one prose sentence
        with no list, while its description still carries a 6-item list);
        then the field's own plain text as a single item. A group with
        nothing at all stays empty -- chips_section already renders that as
        no group, and must keep doing so.
        """
        en_items = prose_items(activity.get(bokun_field))
        if not en_items and desc_fallback_en:
            en_items = list(desc_fallback_en)
        if not en_items:
            plain = cl(activity.get(bokun_field))
            en_items = [plain] if plain else []
        en_joined = '\n'.join(en_items)

        if reviewed:
            ja_items = prose_items((activity_ja or {}).get(bokun_field))
            if not ja_items and desc_fallback_ja:
                ja_items = list(desc_fallback_ja)
            if not ja_items:
                plain_ja = cl((activity_ja or {}).get(bokun_field))
                ja_items = [plain_ja] if plain_ja else []
            ja_joined = '\n'.join(ja_items) or en_joined
        else:
            # Bokun's Japanese prose content is no more trusted, pre-review,
            # than any other Japanese field -- mirror English exactly as
            # title/sub/lede do above.
            ja_joined = en_joined
        return en_joined, ja_joined

    prose = {'included': prose_group(
        'included', desc_fallback_en=parsed['included'], desc_fallback_ja=parsed_ja_included)}
    for bokun_field, rec_field in PROSE_FIELDS:
        prose[rec_field] = prose_group(bokun_field)

    # Predefined enum chip sets (task 18): a closed vocabulary of API
    # constants, unrelated to the free-text fields above. Bokun's own widget
    # renders these as chips using its own internal wording; through the API
    # we only get the constant, so cms/bokun_labels.py supplies the wording
    # for both languages -- unconditionally, not gated by jaReviewed, because
    # this is our own copy, not Bokun content (see point 4, task 18 brief).
    # An unmapped value must never reach the page as a raw SCREAMING_SNAKE
    # string: it is dropped and reported as a warning instead.
    def enum_chip_group(api_field):
        en_items, ja_items = [], []
        for value in activity.get(api_field) or []:
            lbl = bokun_labels.label(value)
            if lbl is None:
                warnings.append(
                    f'unmapped {api_field} value {value!r}; add a label to '
                    f'cms/bokun_labels.py or it will not render on the page.')
                continue
            en_items.append(lbl[0])
            ja_items.append(lbl[1])
        return '\n'.join(en_items), '\n'.join(ja_items)

    enum_chips = {rec_field: enum_chip_group(api_field)
                  for api_field, rec_field in ENUM_CHIP_FIELDS}

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
            # Photos are not language-specific, so these are read from the
            # English payload for both.
            'photo': _agenda_photo(item)[0],
            'photoBase': _agenda_photo(item)[1],
        })

    photos = activity.get('photos') or []
    cover = (photos[0].get('originalUrl') if photos else '') or ''
    cover_base = cdn_base(photos[0]) if photos else ''
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

    # Zero-touch has one soft spot here: length comes from the rate NAMES, so a
    # tour that genuinely sells two formats under names like "Short course" and
    # "Long course" falls back to the activity duration and the eyebrow quietly
    # understates it. Detect that shape and say so, rather than leaving the
    # client to notice a wrong label on the live site.
    distinct = {(r.get('rate_title') or '').strip()
                for r in rows if (r.get('rate_title') or '').strip()}
    if len(distinct) > 1 and not _length_from_rates(rows):
        warnings.append(
            'sells %d differently-named rates but none says half- or full-day, '
            'so the length falls back to the activity duration. Rename them in '
            'Bokun to include "Half Day"/"Full Day" if both are offered: %s'
            % (len(distinct), sorted(distinct)))

    rec = {
        'id': entry['slug'],
        'bokunId': int(activity['id']),
        'number': entry.get('number') or '',
        'area': entry.get('area') or (activity.get('googlePlace') or {}).get('city') or '',
        # rates before duration: the activity duration understates a tour that
        # also sells a full day (Zen Journey reads 4 hours while selling a
        # 7-hour option), so what is actually bookable wins.
        'length': (entry.get('length') or _length_from_rates(rows)
                   or _length_from_duration(activity.get('durationText'))),
        'themes': entry.get('themes') or [],
        'cover': {'url': cover, 'base': cover_base},
        'hoursEn': cl(activity.get('durationText')),
        'hoursJa': cl((activity_ja or {}).get('durationText')) or cl(activity.get('durationText')),
        'priceEn': bokun_price.format_from(fp, 'en'),
        'priceJa': bokun_price.format_from(fp, 'ja'),
        'priceRows': rows,
        'widgets': entry.get('widgets') or {},
        'jaReviewed': reviewed,
        'route': route,
        'includedEn': prose['included'][0], 'includedJa': prose['included'][1],
        'notIncludedEn': prose['notIncluded'][0], 'notIncludedJa': prose['notIncluded'][1],
        'bringEn': prose['bring'][0], 'bringJa': prose['bring'][1],
        'knowEn': prose['know'][0], 'knowJa': prose['know'][1],
        'includedChipsEn': enum_chips['includedChips'][0],
        'includedChipsJa': enum_chips['includedChips'][1],
        'knowChipsEn': enum_chips['knowChips'][0],
        'knowChipsJa': enum_chips['knowChips'][1],
    }

    # Japanese paragraph counts can differ from English, since the two
    # descriptions are split independently. The renderer pairs by index and
    # falls back to the English paragraph where Japanese runs short.
    rec['ledeParasEn'] = lede_paras
    rec['ledeParasJa'] = parsed_ja_lede or lede_paras

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


def fetch_records(client, cfg, registry_path=None):
    """Resolve the catalogue through all four gates (spec 3.1-3.4), then build
    a record for every tour that survives them.

    Gate 2 ("Published": list membership or the allowlist fallback) is
    resolved once, up front, by catalogue() -- it is what supplies the
    candidate id list to iterate at all. The remaining three gates (tier,
    sluggable, complete) are evaluated per candidate below, in that order,
    because each one needs the activity detail this loop already fetches.

    Every run logs the resolved catalogue (count, id, slug, resolution
    reason) and one line per held-back tour naming its cause, so a tour's
    disappearance is traceable from the build output alone (spec 3.1).

    registry_path defaults to the committed cms/tours-slugs.json (via
    tours_slug's own default); tests pass a scratch path so a fixture using a
    synthetic Bokun id can never write into the real, committed registry.
    """
    corr = tours_config.corrections(cfg)
    today = datetime.now(timezone.utc).date()
    # A year, not a quarter. Price is derived from availability, so a window
    # shorter than a tour's first bookable date silently reports it as unpriced:
    # Swordsmithing's first slot is 10 Nov 2026 and a 75-day window from 26 Aug
    # ended 9 Nov, one day short, so it was wrongly shown as "in preparation".
    end = today + timedelta(days=365)
    records, warnings, raw_texts = [], [], []
    resolved, held_back = [], []

    registry = tours_slug.load_registry(registry_path)
    registry_dirty = False

    ids = catalogue(client, cfg, warnings=warnings)
    for pid in ids:
        entry = tours_config.tour_entry(cfg, pid)
        activity = client.get(f'/activity.json/{pid}?lang=EN')
        activity_ja = client.get(f'/activity.json/{pid}?lang=ja')
        title_en = (activity.get('title') or '').strip()
        title_ja = ((activity_ja or {}).get('title') or '').strip()

        # Gate 1: tier. Belt-and-braces on top of the denylist check already
        # applied inside catalogue() -- publishing an OTA tour now needs two
        # independent mistakes.
        if activity.get('marketplaceVisibilityType') != 'PRIVATE':
            held_back.append((pid, title_en,
                              'not Zenrise-tier (marketplaceVisibilityType is '
                              f'{activity.get("marketplaceVisibilityType")!r}, not PRIVATE)'))
            continue

        # Gate 3: sluggable. A config override always wins; then the frozen
        # registry; then a fresh derivation, which alone requires proof of an
        # English translation (tours_slug.resolve).
        slug, reason = tours_slug.resolve(
            pid, title_en, title_ja, activity.get('languages') or [],
            registry, override=(entry.get('slug') or None))
        if not slug:
            held_back.append((pid, title_en, f'no resolvable slug ({reason})'))
            continue
        if registry.get(str(pid)) != slug:
            registry[str(pid)] = slug
            registry_dirty = True

        # Gate 4: complete. No price is NOT a hold-back -- that renders the
        # existing, correct in-preparation layout.
        photos = activity.get('photos') or []
        missing = []
        if not (photos and (photos[0].get('originalUrl') or '').strip()):
            missing.append('cover photo')
        if not (activity.get('description') or '').strip():
            missing.append('description')
        if missing:
            held_back.append((pid, title_en, f"missing {' and '.join(missing)}"))
            continue

        # number: entry override, else this slug's position in the (now
        # possibly just-extended) registry order -- stable once assigned,
        # because a new key is appended, never inserted mid-order.
        number = entry.get('number') or f'{list(registry.keys()).index(str(pid)) + 1:02d}'

        # area: entry override -> googlePlace.city -> the trailing place name
        # a slug derivation would have dropped from the title -> empty, which
        # must hold the tour back rather than reach (and crash) area_key().
        area = (entry.get('area') or (activity.get('googlePlace') or {}).get('city')
                or _trailing_place(title_en))
        if not area:
            held_back.append((pid, title_en,
                              'no derivable area (no googlePlace.city and no '
                              'trailing place name in the title)'))
            continue

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
                f'[{slug}] Japanese availability request failed '
                f'({e}); price labels fall back to English for this tour.')
        else:
            if availability_ja is None:
                warnings.append(
                    f'[{slug}] Japanese availability returned nothing; '
                    f'price labels fall back to English for this tour.')
        availability_ja = availability_ja or []

        built_entry = dict(entry, slug=slug, number=number, area=area)
        rec, w, texts = to_record(
            activity, activity_ja, availability, availability_ja, built_entry, corr)
        records.append(rec)
        resolved.append((pid, slug, reason))
        warnings += [f'[{rec["id"]}] {x}' for x in w]
        raw_texts += texts

    if registry_dirty:
        tours_slug.save_registry(registry_path, registry)

    warnings.append(Note(f'resolved catalogue: {len(resolved)} tour(s).'))
    for pid, slug, reason in resolved:
        warnings.append(Note(f'  [{pid}] -> {slug} (slug: {reason})'))
    for pid, title, cause in held_back:
        warnings.append(f'held back: Bokun product {pid} ({title!r}) — {cause}.')

    for stale in bokun_text.unused_corrections(raw_texts, corr):
        warnings.append(f'correction no longer matches any source text, safe to '
                        f'prune from tours-config.json: {stale!r}')
    return records, warnings
