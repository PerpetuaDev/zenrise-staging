"""Derive display prices from Bokun availability.

Bokun prices vary along two axes at once: passenger category (Adult / Child /
Infant, via pricingCategories) and group-size tier (minParticipantsRequired /
maxParticipantsRequired). There is therefore no single price per tour. See spec
section 3.5.
"""
SYMBOL = {'JPY': '¥'}


def _money(amount, currency):
    return f'{SYMBOL.get(currency, currency + " ")}{int(amount):,}'


def rows(availability, pricing_categories):
    titles = {c['id']: c.get('title') for c in (pricing_categories or [])}
    for slot in availability or []:
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
            'category': best.get('category')}


def format_from(fp, lang):
    if not fp:
        return ''
    money = _money(fp['amount'], fp['currency'])
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
        cat = r.get('category') or ''
        if lang == 'ja':
            cat = _CAT_JA.get(cat.lower(), cat)
        tier = _tier(r, lang)
        label = f'{cat}, {tier}' if cat and tier else (cat or tier)
        money = _money(r['amount'], r['currency'])
        out.append(f'{label}: {money}' if label else money)
    return out
