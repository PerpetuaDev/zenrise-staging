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


def rows(availability, pricing_categories):
    titles = {c['id']: c.get('title') for c in (pricing_categories or [])}
    for slot in availability or []:
        rates = {r['id']: r for r in slot.get('rates') or []}
        out = []
        for rate in slot.get('pricesByRate') or []:
            for u in rate.get('pricePerCategoryUnit') or []:
                out.append({
                    'category': titles.get(u.get('id')),
                    'min': u.get('minParticipantsRequired'),
                    'max': u.get('maxParticipantsRequired'),
                    'amount': int(u['amount']['amount']),
                    'currency': u['amount']['currency'],
                })
            pb = rate.get('pricePerBooking')
            rate_meta = rates.get(rate.get('activityRateId')) or {}
            # `is False`, not falsy: a rate with no pricedPerPerson info at
            # all (e.g. per-person-only fixtures that omit a 'rates' list)
            # must never be mistaken for group pricing. Getting this the
            # other way round would misprice the per-person tours, which is
            # the worse failure.
            if pb and pb.get('amount') is not None and rate_meta.get('pricedPerPerson') is False:
                out.append({
                    'category': None,
                    'min': rate_meta.get('minPerBooking'),
                    'max': rate_meta.get('maxPerBooking'),
                    'amount': int(pb['amount']),
                    'currency': pb['currency'],
                    'per_booking': True,
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


def format_full(price_rows, lang):
    out = []
    for r in price_rows:
        if r.get('per_booking'):
            cat = 'グループ' if lang == 'ja' else 'Group'
        else:
            cat = r.get('category') or ''
            if lang == 'ja':
                cat = _CAT_JA.get(cat.lower(), cat)
        tier = _tier(r, lang)
        label = f'{cat}, {tier}' if cat and tier else (cat or tier)
        money = _money(r['amount'], r['currency'])
        out.append(f'{label}: {money}' if label else money)
    return out
