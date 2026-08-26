"""Derive display prices from Bokun availability.

Bokun prices vary along two axes at once: passenger category (Adult / Child /
Infant, via pricingCategories) and group-size tier (minParticipantsRequired /
maxParticipantsRequired). There is therefore no single price per tour. See spec
section 3.5.

Bokun also has two entirely different pricing *models* per rate: per-person
(the usual case) and per-booking/group (the whole booking, 1..N people, has
one price). A rate's `pricedPerPerson: false` plus a `pricePerBooking` amount
is the only reliable signal for the group case — the associated pricing
category's `ticketCategory` field can say "ADULT" even though the category is
really a group unit (seen on The Zen Journey), so ticketCategory/category
title must never be used to detect group pricing.
"""
SYMBOL = {'JPY': '¥'}


def _money(amount, currency):
    return f'{SYMBOL.get(currency, currency + " ")}{int(amount):,}'


def _rate_titles(availability):
    """rate id -> title, built from an availability response. Used to look
    up Japanese rate titles from a `?lang=ja` availability call, keyed the
    same way as the English `rates` lookup in rows() below. A rate's title
    doesn't vary by date, only by language, so the first slot that mentions
    a rate id wins."""
    titles = {}
    for slot in availability or []:
        for r in slot.get('rates') or []:
            rid = r.get('id')
            if rid is not None and rid not in titles:
                titles[rid] = r.get('title')
    return titles


def rows(availability, pricing_categories, pricing_categories_ja=None, availability_ja=None):
    titles = {c['id']: c.get('title') for c in (pricing_categories or [])}
    # Japanese counterparts of the same two lookups. Both default to empty/
    # None so an unreviewed tour (which the caller deliberately withholds
    # these from) or a failed/absent Japanese availability call yields rows
    # with category_ja/rate_title_ja unset, and format_full falls back to
    # _CAT_JA or the English string exactly as it did before this field
    # existed — the pattern is to add a field, not overload one.
    titles_ja = {c['id']: c.get('title') for c in (pricing_categories_ja or [])}
    rate_titles_ja = _rate_titles(availability_ja)
    for slot in availability or []:
        rates = {r['id']: r for r in slot.get('rates') or []}
        out = []
        for rate in slot.get('pricesByRate') or []:
            # The rate's own title, e.g. "Group(1~6) Harf Day" — carried on
            # every row from this rate so a group row can be labelled by it
            # (task 14). Per-person rows carry it too but ignore it in
            # format_full: their label is category + tier, as before.
            rate_meta = rates.get(rate.get('activityRateId')) or {}
            rate_title = rate_meta.get('title')
            rate_title_ja = rate_titles_ja.get(rate.get('activityRateId'))
            for u in rate.get('pricePerCategoryUnit') or []:
                out.append({
                    'category': titles.get(u.get('id')),
                    'category_ja': titles_ja.get(u.get('id')),
                    'min': u.get('minParticipantsRequired'),
                    'max': u.get('maxParticipantsRequired'),
                    'amount': int(u['amount']['amount']),
                    'currency': u['amount']['currency'],
                    'rate_title': rate_title,
                    'rate_title_ja': rate_title_ja,
                })
            pb = rate.get('pricePerBooking')
            # `is False`, not falsy: a rate with no pricedPerPerson info at
            # all (e.g. per-person-only fixtures that omit a 'rates' list)
            # must never be mistaken for group pricing. Getting this the
            # other way round would misprice the per-person tours, which is
            # the worse failure.
            if pb and pb.get('amount') is not None and rate_meta.get('pricedPerPerson') is False:
                out.append({
                    'category': None,
                    'category_ja': None,
                    'min': rate_meta.get('minPerBooking'),
                    'max': rate_meta.get('maxPerBooking'),
                    'amount': int(pb['amount']),
                    'currency': pb['currency'],
                    'per_booking': True,
                    'rate_title': rate_title,
                    'rate_title_ja': rate_title_ja,
                })
                # extraPricePerCategoryUnit (an extra amount per additional
                # participant on some group rates) is deliberately ignored:
                # its exact semantics are unconfirmed and it must not enter
                # the headline price.
        if out:
            return out
    return []


def _is_adult(row):
    return (row.get('category') or '').lower().startswith('adult')


def from_price(price_rows):
    if not price_rows:
        return None
    adult = [r for r in price_rows if _is_adult(r)]
    pool = adult or price_rows
    best = min(pool, key=lambda r: r['amount'])
    return {'amount': best['amount'], 'currency': best['currency'],
            'category': best.get('category'), 'per_booking': bool(best.get('per_booking'))}


def format_from(fp, lang):
    if not fp:
        return ''
    money = _money(fp['amount'], fp['currency'])
    if fp.get('per_booking'):
        return f'{money}〜（1グループ）' if lang == 'ja' else f'from {money} per group'
    adult = _is_adult(fp)
    if lang == 'ja':
        return f'{money}〜（大人おひとり）' if adult else f'{money}〜'
    return f'from {money} per adult' if adult else f'from {money}'


def _tier(row, lang):
    mn, mx = row.get('min'), row.get('max')
    if not mn and not mx:
        return ''
    if mn and mx and mn != mx:
        return f'{mn}–{mx}名' if lang == 'ja' else f'{mn}–{mx} guests'
    n = mn or mx
    return f'{n}名' if lang == 'ja' else (f'{n} guest' if n == 1 else f'{n} guests')


_CAT_JA = {'adult': '大人', 'adults': '大人', 'child': '子供',
           'children': '子供', 'infant': '幼児'}


def _merge_key(r):
    if r.get('per_booking'):
        return ('booking', r.get('rate_title'))
    return ('person', r.get('category'))


def _merge(price_rows):
    """Collapse rows that share a label and an amount into one row spanning
    their combined min/max.

    Bokun's real availability often lists one row per exact participant
    count at the same price (e.g. 3, 4, 5 and 6 guests all at ¥21,000)
    rather than a single ready-made range, so without this the breakdown
    would repeat the same price several times. Rows are only merged when
    both the label key (category, or rate title for a group row) and the
    amount match — different amounts always stay separate rows. See task 14.
    """
    merged, index = [], {}
    for r in price_rows or []:
        key = (_merge_key(r), r['amount'], r['currency'])
        if key not in index:
            index[key] = len(merged)
            merged.append(dict(r))
            continue
        m = merged[index[key]]
        if r.get('min') is not None:
            m['min'] = r['min'] if m.get('min') is None else min(m['min'], r['min'])
        if r.get('max') is not None:
            m['max'] = r['max'] if m.get('max') is None else max(m['max'], r['max'])
    # Ascending by group size, so the smallest (priciest, per-person) tier
    # leads — matches how the client's own price lists read.
    merged.sort(key=lambda r: (r.get('min') is None, r.get('min') or 0))
    return merged


def rows_full(price_rows, lang):
    """The full breakdown as (label, formatted money) pairs, merged and
    ordered for display. format_full() below is a thin string-joining
    wrapper over this — the one mechanism the two share.
    """
    out = []
    for r in _merge(price_rows):
        if r.get('per_booking'):
            # Precedence for a group row's label: the Japanese rate title
            # from Bokun, if one has been entered; otherwise the English
            # title verbatim (rate titles are the client's own text,
            # including their typos, and are never corrected or invented
            # here — see the group-pricing tests).
            title = (lang == 'ja' and r.get('rate_title_ja')) or r.get('rate_title')
            if title:
                label = title
            else:
                cat = 'グループ' if lang == 'ja' else 'Group'
                tier = _tier(r, lang)
                label = f'{cat}, {tier}' if tier else cat
        else:
            cat = r.get('category') or ''
            if lang == 'ja':
                # Precedence: the Japanese category title from Bokun, then
                # the hand-written Adult/Child/Infant fallback, then the
                # English string — never invented, never left blank.
                cat = r.get('category_ja') or _CAT_JA.get(cat.lower(), cat)
            tier = _tier(r, lang)
            label = f'{cat}, {tier}' if cat and tier else (cat or tier)
        money = _money(r['amount'], r['currency'])
        out.append((label, money))
    return out


def format_full(price_rows, lang):
    return [f'{label}: {money}' if label else money
            for label, money in rows_full(price_rows, lang)]


def has_price_breakdown(price_rows):
    """False when a breakdown would show nothing beyond the headline 'from'
    price: no rows, one row, or several rows that all carry the same
    amount. The caller should render nothing in that case (task 14, rule 5).
    """
    amounts = {r['amount'] for r in (price_rows or [])}
    return len(amounts) > 1
