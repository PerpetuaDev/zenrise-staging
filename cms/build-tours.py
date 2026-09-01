#!/usr/bin/env python3
"""Render the tours section from the tours content model: one tour-<id>.html per
tour, plus the card grid in tours.html and the tile grid in index.html (both between
CMS:...:start/end markers).

Records come from Bokun via cms/tours_build_source.load_records(): --source
bokun (default) fetches live from the client's Bokun account, --source cache
reads the committed cms/tours-cache.json without touching the network, and
--live is retained as an alias for --source bokun. A failed Bokun fetch falls
back to cms/tours-cache.json automatically so an outage never empties the
tours pages; with no cache at all the build fails loudly instead. Route stops
come from Bokun's agendaItems, not a standalone fixture.

Homepage tile order follows site-config.featuredTours when present (fixture:
cms/site-config-fixture.json), else the tours list order.
"""

import glob, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = 'https://zenrise.jp'

class BuildError(Exception):
    pass


AREA_KEY = {'Kamakura': 'tours_area_kamakura', 'Enoshima': 'tours_area_enoshima', 'Yokohama': 'tours_area_yokohama'}
AREA_JA = {'Kamakura': '鎌倉', 'Enoshima': '江ノ島', 'Yokohama': '横浜'}
LEN_KEY = {'Half-day': 'tours_len_half', 'Full-day': 'tours_len_full',
           'Full / Half-day': 'tours_len_both'}


def _themes():
    sys.path.insert(0, os.path.dirname(HERE))
    from cms import tours_themes
    return tours_themes


def theme_slugs(themes):
    """Validate that every theme is a live slug. Bokun and tours-config.json
    both speak slugs, so this is a gate rather than a translation."""
    tt = _themes()
    for t in themes:
        if t not in tt.I18N_KEY:
            raise BuildError(
                f'theme {t!r} is not a live theme slug. Valid slugs are '
                f'{", ".join(tt.ORDER)} -- add it to cms/tours_themes.py, or '
                f'correct the themes value in cms/tours-config.json.')
    return list(themes)


def filter_rows(models):
    """The area and theme chip rows on tours.html, built from the catalogue.

    Only values a tour actually has get a chip, so a filter can never come up
    empty. A row with fewer than two distinct values is dropped whole: one chip
    filters nothing, because everything it can reveal is already on screen.
    """
    tt = _themes()
    areas, themes = [], set()
    for m in models:
        if m['area'] not in areas:
            areas.append(m['area'])
        themes.update(theme_slugs(m['themes']))

    # Validate every area before deciding whether the row renders: iterating
    # AREA_KEY below would silently skip a place we have no key for, and the
    # tour would then fail later in card() instead of being held back here.
    for a in areas:
        area_key(a)

    rows = []
    if len(areas) > 1:
        buttons = ['<button type="button" class="chip on" data-area="all" '
                   'data-i18n="tours_area_all">All areas</button>']
        for a in AREA_KEY:                       # canonical order, not catalogue order
            if a in areas:
                buttons.append(
                    f'<button type="button" class="chip" data-area="{a.lower()}" '
                    f'data-i18n="{area_key(a)}">{a}</button>')
        rows.append(('areas', 'Filter by area', buttons))

    if len(themes) > 1:
        buttons = [f'<button type="button" class="chip" data-theme="{s}" '
                   f'data-i18n="{tt.I18N_KEY[s]}">{tt.LABEL_EN[s]}</button>'
                   for s in tt.ORDER if s in themes]
        rows.append(('themes', 'Filter by theme', buttons))

    if not rows:
        return ''

    # The label has to describe what actually rendered: with every tour in one
    # place the area row drops, and "Browse by area" would then sit above a row
    # of experience types.
    if rows[0][0] == 'areas':
        label_key, label_en = 'tours_filter_label', 'Browse by area'
    else:
        label_key, label_en = 'tours_filter_label_theme', 'Browse by experience'
    out = [f'        <span class="label" data-i18n="{label_key}">{label_en}</span>']

    for cls, aria, buttons in rows:
        inner = '\n'.join('          ' + b for b in buttons)
        out.append(f'        <div class="chip-row {cls}" role="group" '
                   f'aria-label="{aria}">\n{inner}\n        </div>')
    return '\n'.join(out)


def area_key(area):
    try:
        return AREA_KEY[area]
    except KeyError:
        raise BuildError(
            f'area {area!r} has no i18n key. Add it to AREA_KEY and AREA_JA in '
            f'build-tours.py and to the filter buttons in tours.html, or correct '
            f'the area value in cms/tours-config.json.')


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;'))


def render(tpl, slots):
    for k, v in slots.items():
        tpl = tpl.replace('{{%s}}' % k, v)
    leftover = re.findall(r'\{\{[A-Z_]+\}\}', tpl)
    assert not leftover, f'unfilled template slots: {leftover}'
    return tpl


def dict_script(en, ja):
    payload = json.dumps({'en': en, 'ja': ja}, ensure_ascii=False,
                         separators=(',', ':')).replace('</', '<\\/')
    return f'<script>window.ZENRISE_CMS_DICT = {payload};</script>'


def load_template(name):
    return open(os.path.join(HERE, 'templates', name)).read()


def lines(s):
    return [l.strip() for l in (s or '').splitlines() if l.strip()]


def fetch_tours(source, require_live=False):
    """Records + config. microCMS is no longer a tours source: Bokun is.

    See docs/superpowers/specs/2026-08-25-bokun-integration-design.md section 3.
    """
    sys.path.insert(0, os.path.dirname(HERE))
    from cms import tours_build_source
    records, cfg, warnings = tours_build_source.load_records(
        source, require_live=require_live)
    from cms.bokun_source import Note
    for w in warnings:
        print('NOTE:' if isinstance(w, Note) else 'WARNING:', w)
    return records, cfg


def tour_model(a):
    m = {'id': a['id'], 'K': 'tours_' + a['id'], 'num': a['number'],
         'bokun_id': a.get('bokunId'), 'widgets': a.get('widgets') or {},
         'price_rows': a.get('priceRows') or []}
    for f in ('title', 'sub', 'hours', 'coverCaption', 'price', 'lede',
              'included', 'notIncluded', 'bring', 'know',
              'includedChips', 'knowChips'):
        m[f] = ((a.get(f + 'En') or '').strip(), (a.get(f + 'Ja') or '').strip())
    # Paragraph list, falling back to the joined lede for cache entries written
    # before this existed.
    m['lede_paras'] = (list(a.get('ledeParasEn') or []),
                       list(a.get('ledeParasJa') or []))
    m['area'] = a['area']
    m['length'] = a['length']
    m['themes'] = a.get('themes') or []
    m['cover'] = (a.get('cover') or {}).get('url', '')
    # Bokun's image CDN base, when the photo came from Bokun. Sample tours carry
    # a plain URL and no base, so they fall back to that URL untouched.
    m['cover_base'] = (a.get('cover') or {}).get('base', '') or ''
    # Price is per tour and comes from Bokun, so there is no shared length key.
    m['price_key'] = None
    m['price_en'] = m['price'][0]
    m['price_ja'] = m['price'][1]
    m['route'] = a.get('route') or []
    return m


def meta_desc(m):
    text = m['sub'][0] or m['lede'][0] or f"{m['title'][0]} — a Zenrise private experience."
    if len(text) <= 160:
        return text
    cut = text[:160].rsplit(' ', 1)[0]
    return cut.rstrip(' ,.;:') + '…'


def sized(base, fallback, width, height=None):
    """A CDN URL at the size actually displayed, or the fallback URL.

    Bokun's originals are around 4000x2800. Serving one to a 430px card is the
    reason the tours page loaded slowly, and no amount of CSS fixes that -- the
    browser downloads the whole file first. mode=crop is only used where the slot
    has a fixed aspect, so a width-only request never distorts.
    """
    if not base:
        return fallback
    q = f'?w={width}'
    if height:
        q += f'&h={height}&mode=crop'
    return base + q


def cover_at(m, width, height=None):
    return sized(m.get('cover_base'), m['cover'], width, height)


def json_ld(m):
    data = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        'name': m['title'][0],
        'description': meta_desc(m),
        'url': f"{SITE}/tour-{m['id']}.html",
        'brand': {'@type': 'Brand', 'name': 'Zenrise'},
    }
    if m['cover']:
        data['image'] = cover_at(m, 1200, 630)
    rows = m.get('price_rows') or []
    if rows:
        low = min(rows, key=lambda r: r['amount'])
        data['offers'] = {
            '@type': 'Offer',
            'price': low['amount'],
            'priceCurrency': low['currency'],
            'url': f"{SITE}/tour-{m['id']}.html#book",
        }
    body = json.dumps(data, ensure_ascii=False, indent=1)
    # A literal </script> inside copy would close the tag early.
    body = body.replace('</', '<\\/')
    return f'<script type="application/ld+json">\n{body}\n</script>'


def write_tours_index(models):
    """Slugs for build-news.py's sitemap, which is the single sitemap writer."""
    path = os.path.join(HERE, 'tours-index.json')
    with open(path, 'w') as f:
        json.dump([m['id'] for m in models], f, indent=1)


def party_range(price_rows):
    """The party size a tour can actually take, read from its rate tiers.

    Bokun prices per tier -- candle-making sells 1-2, then 3, then 4 -- so the
    real range is the widest pair across the tiers, not a house assumption. It
    used to be hardcoded as 1-6 on every tour, which invited parties Bokun has
    no price for (ikebana is priced for two people at most).
    """
    lo = [r['min'] for r in price_rows or [] if r.get('min') is not None]
    hi = [r['max'] for r in price_rows or [] if r.get('max') is not None]
    if not lo or not hi:
        return None
    return min(lo), max(hi)


def party_label(price_rows, lang):
    """'1-4 travelers' / '1〜4名', or '' when no tier carries bounds."""
    r = party_range(price_rows)
    if not r:
        return ''
    lo, hi = r
    if lang == 'ja':
        return f'{lo}〜{hi}名' if lo != hi else f'{hi}名'
    if lo != hi:
        return f'{lo}\u2013{hi} travelers'
    return '1 traveler' if hi == 1 else f'{hi} travelers'


def cta_eyebrow(price, party):
    """Join price and party size, dropping the separator when either is absent
    -- an in-preparation tour has neither."""
    return ' \u30fb '.join(x for x in (price, party) if x)


def base_dict(m):
    """Keys shared by every rendering of this tour (cards, tiles, detail head)."""
    K = m['K']
    en = {K + '_name': m['title'][0], K + '_sub': m['sub'][0], K + '_hours': m['hours'][0],
          K + '_title': f"{m['title'][0]} — Zenrise",
          K + '_eyebrow': f"Tour No. {m['num']}",
          K + '_cap': m['coverCaption'][0],
          K + '_cta_eyebrow': cta_eyebrow(m['price_en'],
                                          party_label(m['price_rows'], 'en'))}
    ja = {K + '_name': m['title'][1], K + '_sub': m['sub'][1], K + '_hours': m['hours'][1],
          K + '_title': f"{m['title'][1]} — Zenrise",
          K + '_eyebrow': f"ツアー No. {m['num']}",
          K + '_cap': m['coverCaption'][1],
          K + '_cta_eyebrow': cta_eyebrow(m['price_ja'],
                                          party_label(m['price_rows'], 'ja'))}
    en[K + '_price'] = m['price_en']
    ja[K + '_price'] = m['price_ja']
    return en, ja


def og_image(m):
    if not m['cover']:
        return f'{SITE}/assets/shrines/temple-gate-pine.jpg'
    url = cover_at(m, 1200, 630)
    return url if url.startswith('http') else f"{SITE}/{url}"


def common_slots(m):
    return {
        'ID': m['id'], 'K': m['K'], 'NUM': m['num'],
        'TITLE_EN': esc(m['title'][0]),
        'META_DESC': esc(meta_desc(m)),
        'JSON_LD': json_ld(m),
        'OG_IMAGE': esc(og_image(m)),
        'COVER_URL': esc(cover_at(m, 1900)),
        'CAP_EN': esc(m['coverCaption'][0]),
        'AREA_KEY': area_key(m['area']), 'AREA_EN': m['area'],
        'LEN_KEY': LEN_KEY[m['length']], 'LEN_EN': m['length'],
        'HOURS_EN': esc(m['hours'][0]),
        'PRICE_KEY': m['price_key'] or (m['K'] + '_price'),
        'PRICE_EN': esc(m['price_en']),
        'CTA_EYEBROW_EN': esc(cta_eyebrow(m['price_en'],
                                          party_label(m['price_rows'], 'en'))),
        'WIDGET_BLOCK': '', 'CHIPS_SECTION': '', 'ROUTE_SECTION': '',
    }


def chips(m, field, prefix, en, ja):
    """Render <span class="chip"> items from m[field] (an (en, ja) tuple of
    newline-joined short labels), or '' when there are none.

    Chip content is Bokun's closed enum vocabulary run through
    cms/bokun_labels.py (task 18) -- short labels, which is what this
    component was built for. Free-text sentences go through prose() instead.
    """
    if field is None or not m[field][0]:
        return ''
    K = m['K']
    out = []
    for i, (e, j) in enumerate(zip(lines(m[field][0]), lines(m[field][1])), 1):
        en[f'{K}_{prefix}_{i}'] = e
        ja[f'{K}_{prefix}_{i}'] = j
        out.append(f'              <span class="chip" data-i18n="{K}_{prefix}_{i}">{esc(e)}</span>')
    return '\n'.join(out)


def prose(m, field, prefix, en, ja):
    """Render <li> items from m[field] (an (en, ja) tuple of newline-joined
    sentences), or '' when there are none.

    Prose is Bokun's free-text fields (task 18): full sentences, sometimes
    long ones, so it renders as a stacked list with a hairline separator
    between items rather than the bordered, padded box chips() draws --
    see .grp .prose in tour-detail.html.
    """
    if not m[field][0]:
        return ''
    K = m['K']
    out = []
    for i, (e, j) in enumerate(zip(lines(m[field][0]), lines(m[field][1])), 1):
        en[f'{K}_{prefix}_{i}'] = e
        ja[f'{K}_{prefix}_{i}'] = j
        out.append(f'              <li data-i18n="{K}_{prefix}_{i}">{esc(e)}</li>')
    return '\n'.join(out)


# Each group may carry chips (a closed Bokun enum, task 18), prose (Bokun
# free text), or both -- chips first, prose second, mirroring Bokun's own
# split between `inclusions`/`knowBeforeYouGoItems` and `included`/
# `excluded`/`requirements`/`attention`. Only Included and Good to know have
# an enum counterpart in Bokun; Not included and What to bring are text-only,
# so their chip field/prefix are None and chips() is never called for them.
# (prose field, prose prefix, chip field or None, chip prefix or None, i18n key, label)
CHIP_GROUPS = (('included', 'incp', 'includedChips', 'inc', 'td_included', 'Included'),
               ('notIncluded', 'nincp', None, None, 'td_notinc', 'Not included'),
               ('bring', 'brgp', None, None, 'td_bring', 'What to bring'),
               ('know', 'knop', 'knowChips', 'kno', 'td_know', 'Good to know'))


def _chip_groups(m, en, ja, want):
    """The four Bokun inclusion groups, rendered with only one kind of content.

    want='chips' keeps the closed-vocabulary enum chips; want='prose' keeps the
    free-text lines. They are split across two places on the page because they
    behave differently: chips are short and scannable and belong under the lede,
    while the prose is dense and was crowding it out. A group with nothing of
    the requested kind renders no heading over nothing.

    See spec 3.4 and 3.4.1.
    """
    groups = []
    for prose_field, prose_prefix, chip_field, chip_prefix, key, label in CHIP_GROUPS:
        if want == 'chips':
            body_html = chips(m, chip_field, chip_prefix, en, ja)
            wrapper = ('            <div class="chips">\n', '\n            </div>')
        else:
            body_html = prose(m, prose_field, prose_prefix, en, ja)
            wrapper = ('            <ul class="prose">\n', '\n            </ul>')
        if not body_html.strip():
            continue
        groups.append(
            '          <div class="grp">\n'
            f'            <span class="label" data-i18n="{key}">{label}</span>\n'
            + wrapper[0] + body_html + wrapper[1] + '\n'
            '          </div>')
    if not groups:
        return ''
    return ('        <div class="chip-groups">\n'
            + '\n'.join(groups)
            + '\n        </div>')


def chips_section(m, en, ja):
    """The scannable enum chips, shown directly under the lede."""
    return _chip_groups(m, en, ja, 'chips')


def other_info_section(m, en, ja):
    """The dense free-text inclusion lines, as their own section below the route.

    Previously these sat under the lede alongside the chips, which buried the
    description under several hundred words of logistics. They are a peer of the
    route section now, and laid out in two columns on wide screens so the
    longest group does not read as one unbroken wall.
    """
    body = _chip_groups(m, en, ja, 'prose')
    if not body:
        return ''
    # Cancellation, insurance and payment are general terms, set out in full and
    # more precisely on terms.html. Pointing there keeps this block to what is
    # specific to the tour, and gives the client somewhere to send the general
    # clauses that currently duplicate the terms page.
    return f'''    <section class="other-wrap" data-screen-label="07 Tour detail — Other info">
      <div class="other">
        <h2 data-i18n="td_other">Other info.</h2>
{body}
        <p class="other-terms">
          <a href="terms.html">
            <span class="u" data-i18n="td_other_terms">Cancellation, insurance and payment terms in full</span><span class="ar">&nbsp;→</span>
          </a>
        </p>
      </div>
    </section>'''


# A stop duration written at the head of the body, e.g. "30min The history of…".
# Only some products carry these, so the time cell is optional per row.
# Two alternatives on purpose: the ASCII units keep a word boundary so "min"
# cannot match inside a longer word, while the Japanese units need none —
# \b between two CJK characters does not behave as it does between letters,
# and quantifying it (\b?) is a regex error, not a shortcut.
_STOP_TIME = re.compile(
    r'^\s*(\d+\s*(?:min|mins|minute|minutes|hr|hrs|hour|hours)\b'
    r'|\d+\s*(?:分|時間))[\s:·\-–—]*',
    re.I)


def split_stop_time(body):
    """('30min', 'The history of the art…') or (None, body) when there is none."""
    m = _STOP_TIME.match(body or '')
    if not m:
        return None, (body or '').strip()
    return m.group(1).strip(), body[m.end():].strip()


def route_rows(m, en, ja):
    """Route rows from Bokun agendaItems.

    Replaces the tour-routes.json version. Bokun has no structured per-stop
    time, distance, thumbnail or Japanese variant. Distance and thumbnail are
    gone. A duration is rendered when the copy carries one at the head of the
    body, and the cell is omitted when it does not, so a tour without timings
    shows no empty column. See ledger Ruling B (amended by Ruling D).
    """
    K = m['K']
    rows = []
    for i, st in enumerate(m['route'], 1):
        n = f'{i:02d}'
        time, body = split_stop_time(st['body'])
        # A stop may carry Japanese (sample tours do, and Bokun products will
        # once the client fills the JA slot). Fall back to the English string so
        # the JA dictionary is always complete rather than missing keys.
        ja_title = st.get('titleJa') or st['title']
        ja_time, ja_body = (split_stop_time(st['bodyJa']) if st.get('bodyJa')
                            else (time, body))
        en[f'{K}_rt_{n}_name'] = st['title']; ja[f'{K}_rt_{n}_name'] = ja_title
        en[f'{K}_rt_{n}_note'] = body;        ja[f'{K}_rt_{n}_note'] = ja_body
        if time:
            en[f'{K}_rt_{n}_time'] = time
            ja[f'{K}_rt_{n}_time'] = ja_time or time
        time_cell = (f'<div class="r-time" data-i18n="{K}_rt_{n}_time">{esc(time)}</div>'
                     if time else '')
        # The stop thumbnail, restored now that Bokun carries a key photo per
        # agenda item. When there is one the stop number sits on the photo, as
        # the original design had it; without one it keeps its own cell, so a
        # tour whose agenda has no photos is unchanged.
        photo = sized(st.get('photoBase'), (st.get('photo') or '').strip(), 420, 280)
        if photo:
            # alt is empty on purpose: the stop's own heading is right beside it,
            # so alt text here would only repeat it to a screen reader.
            # aria-hidden and no role: purely decorative, since the stop's own
            # heading sits beside it. role="img" would contradict aria-hidden.
            num_cell = (f'<div class="r-pic" aria-hidden="true" '
                        f'style="background-image: url(\'{esc(photo)}\')">'
                        f'<span class="rn">{n}</span></div>')
        else:
            num_cell = f'<div class="r-num">{n}</div>'
        classes = 'r-row' + (' has-pic' if photo else '') + ('' if time else ' no-time')
        rows.append(
            f'        <div class="{classes}">\n'
            f'          {num_cell}\n'
            f'          {time_cell}\n'
            f'          <div><h3 data-i18n="{K}_rt_{n}_name">{esc(st["title"])}</h3>'
            f'<p class="r-note" data-i18n="{K}_rt_{n}_note">{esc(body)}</p></div>\n'
            '        </div>')
    return '\n'.join(rows)


def route_section(m, en, ja):
    """The whole route block, or nothing.

    Candle-making and Swordsmithing have no agendaItems, so they must not render
    an empty route heading. See spec 3.4.
    """
    rows = route_rows(m, en, ja)
    if not rows.strip():
        return ''
    return f'''    <section class="route-wrap" data-screen-label="07 Tour detail — Route">
      <div class="route">
        <h2 data-i18n="td_route">The route.</h2>

{rows}

      </div>
    </section>'''


WIDGET_HOST = 'https://widgets.bokun.io'
WIDGET_LOADER = (WIDGET_HOST +
                 '/assets/javascripts/apps/build/BokunWidgetsLoader.js?bookingChannelUUID=')


def price_breakdown_block(m, en, ja):
    """The full price breakdown, placed above the widget mount inside the
    booking aside, so a visitor reads it alongside the widget quoting a
    different number for their party size (task 14; see spec section 3.5).

    Renders nothing when the breakdown would only restate the headline
    "from" price (bokun_price.has_price_breakdown). Feeds both languages
    into the per-page i18n dicts like every other generated string, keyed
    tours_<slug>_pb_<n>, so the block switches with the language toggle.

    Replaces the PRICE_ROWS slot from an earlier task: format_full's output
    had never been consumed by any template. There is now exactly one
    mechanism (bokun_price.rows_full) behind both this block and
    format_full.
    """
    sys.path.insert(0, os.path.dirname(HERE))
    from cms import bokun_price
    price_rows = m.get('price_rows') or []
    if not bokun_price.has_price_breakdown(price_rows):
        return ''
    K = m['K']
    en_rows = bokun_price.rows_full(price_rows, 'en')
    ja_rows = bokun_price.rows_full(price_rows, 'ja')
    items = []
    for i, ((le, me), (lj, mj)) in enumerate(zip(en_rows, ja_rows), 1):
        key = f'{K}_pb_{i}'
        en[key] = f'<span class="pb-label">{esc(le)}</span><span class="pb-amt">{esc(me)}</span>'
        ja[key] = f'<span class="pb-label">{esc(lj)}</span><span class="pb-amt">{esc(mj)}</span>'
        items.append(f'              <li class="pb-row" data-i18n-html="{key}">'
                     f'<span class="pb-label">{esc(le)}</span><span class="pb-amt">{esc(me)}</span></li>')
    note_key = f'{K}_pb_note'
    en[note_key] = 'Full price breakdown'
    ja[note_key] = '料金の内訳'
    return ('          <div class="price-breakdown">\n'
            f'            <p class="pb-note" data-i18n="{note_key}">Full price breakdown</p>\n'
            '            <ul class="pb-list">\n'
            + '\n'.join(items) + '\n'
            '            </ul>\n'
            '          </div>\n')


def widget_block(m, price_html=''):
    """Bokun calendar widget mount for a priced tour.

    The widget is a cross-origin iframe, so it cannot inherit our CSS or the
    Adobe kit; colour is configured in Bokun's panel. See spec section 3.6.

    price_html (task 14) renders above the widget mount, inside the same
    aside, in both the normal and the widget-not-yet-configured case.
    """
    widgets = m.get('widgets') or {}
    en = widgets.get('en')
    if not en:
        return (f'        <aside class="cal-missing" id="book" data-widget-missing="{m["id"]}">\n'
                f'{price_html}'
                f'          <p>Booking widget not yet configured for this tour.</p>\n'
                f'        </aside>')
    channel = en.split('/')[0]
    base = f'{WIDGET_HOST}/online-sales/{en}'
    loader = f'{WIDGET_LOADER}{channel}'
    # Bokun's widget app reads a `lang` param off data-src -- and when it finds
    # one it also hides its own language selector, which is what we want since
    # the page already has a switcher and the two can otherwise disagree. With
    # no param it falls back to <html lang>, read ONCE at init, which is why the
    # calendar only followed the page after a manual refresh.
    #
    # The inline script below runs synchronously, before the async loader, so
    # the mount already carries the stored language by the time Bokun scans it.
    return f'''        <aside class="cal" id="book" data-screen-label="07 Tour detail — Booking">
          <h2 class="cal-h" data-i18n="td_book_heading">Book your spot</h2>
{price_html}          <div class="bokunWidget" data-src="{base}?lang=en" data-widget-base="{base}"></div>
          <script>(function(){{
            var m = document.querySelector('.bokunWidget[data-widget-base]');
            if (!m) return;
            var stored = 'en';
            try {{ stored = localStorage.getItem('zenrise-lang') || 'en'; }} catch (e) {{}}
            var want = stored === 'ja' ? 'ja' : 'en';
            m.setAttribute('data-src', m.getAttribute('data-widget-base') + '?lang=' + want);
            m.setAttribute('data-widget-lang', want);
          }})();</script>
          <script type="text/javascript" src="{loader}" async></script>
          <script>(function(){{
            // Language change reloads the page rather than re-mounting in place.
            // Re-mounting does swap correctly -- the new iframe carries lang=ja --
            // but it then hangs at the loader's 700px "Loading booking engine"
            // placeholder, because Bokun's app script has already initialised and
            // its parent/iframe handshake does not re-establish for a second
            // mount. A reload is what a guest was otherwise doing by hand.
            //
            // lang.js writes the choice to localStorage BEFORE it calls its
            // listeners, so by the time this runs the stored language is already
            // the new one and the inline script above picks it up on the way back.
            function hook() {{
              if (!window.ZenriseI18n || !window.ZenriseI18n.onChange) return false;
              window.ZenriseI18n.onChange(function (l) {{
                var want = l === 'ja' ? 'ja' : 'en';
                var m = document.querySelector('.bokunWidget[data-widget-base]');
                // Only reload when the widget is actually showing the other
                // language, so this cannot loop and does nothing on pages or
                // states where no widget is mounted.
                if (m && m.getAttribute('data-widget-lang') !== want) {{
                  window.location.reload();
                }}
              }});
              return true;
            }}
            if (!hook()) {{
              var tries = 0;
              var iv = setInterval(function () {{
                if (hook() || ++tries > 40) clearInterval(iv);
              }}, 100);
            }}
          }})();</script>
          <noscript><a class="c-go" href="go/{m['id']}/">Book this experience&nbsp;&nbsp;→</a></noscript>
        </aside>'''


def go_redirect_html(m):
    """No-JS and email/social fallback: a bare redirect to the Bokun widget."""
    en = (m.get('widgets') or {}).get('en')
    if not en:
        return None
    url = f'{WIDGET_HOST}/online-sales/{en}'
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Redirecting to booking…</title>
  <meta name="robots" content="noindex">
  <meta http-equiv="refresh" content="0; url={url}">
  <script>location.replace("{url}");</script>
</head>
<body>
  <p>Redirecting to the booking page… <a href="{url}">Continue here</a> if nothing happens.</p>
</body>
</html>
'''


def write_go_redirects(models):
    written = []
    for m in models:
        html = go_redirect_html(m)
        if not html:
            continue
        d = os.path.join(ROOT, 'go', m['id'])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'index.html'), 'w') as f:
            f.write(html)
        written.append(f"go/{m['id']}/")
    return written


# go/ directories that are maintained by hand and must never be touched by
# the cleanup below. Both are live advertising links to OTA-tier tours on a
# DIFFERENT Bokun booking channel (e2350ad8-...) from the one this site's
# widgets use, and both are outside this system entirely:
#   kamakura -> a single experience, linked from the Instagram profile
#   tours    -> the 'OTA Tours' product list (Bokun list 113115)
# Guarded by name even though no configured slug can currently collide with
# either -- see cms/tests/test_go_redirects.py.
HAND_MAINTAINED_GO_SLUGS = ('kamakura', 'tours')


def cleanup_stale_pages(models, root=None):
    """Remove tour-<slug>.html and go/<slug>/ for any slug that is frozen in
    the slug registry but is NOT in this build's resolved catalogue.

    A tour drops out of the catalogue (spec 3.1: switched to PUBLIC, taken
    off the Website product list, etc) without ever being un-frozen from the
    registry -- its slug must stay reserved so it can never be reused by a
    different tour. But the build otherwise only ever writes pages, so its
    orphaned page and redirect would stay reachable forever. This is that
    missing removal step (task-3-4 brief).

    Two hard rules:
    - The go/ directories in HAND_MAINTAINED_GO_SLUGS (kamakura, tours) are
      live advertising links to OTA-tier tours on another booking channel,
      entirely outside this system, and must never be touched -- guarded by
      name above even though no configured slug can currently collide with
      them (see cms/tests/test_go_redirects.py TestInstagramRedirectPreserved
      and test_stale_cleanup.py test_every_hand_maintained_go_slug_is_guarded).
    - A tour-*.html on disk whose slug is in neither the resolved catalogue
      nor the registry is unaccounted for: warn and leave it alone rather
      than guess.
    """
    root = root or ROOT
    sys.path.insert(0, os.path.dirname(HERE))
    from cms import tours_slug
    registry = tours_slug.load_registry()
    catalogue_slugs = {m['id'] for m in models}

    removed = []
    for slug in registry.values():
        if slug in catalogue_slugs or slug in HAND_MAINTAINED_GO_SLUGS:
            continue
        page = os.path.join(root, f'tour-{slug}.html')
        go_dir = os.path.join(root, 'go', slug)
        if os.path.isfile(page):
            os.remove(page)
            removed.append(f'tour-{slug}.html')
        if os.path.isdir(go_dir):
            shutil.rmtree(go_dir)
            removed.append(f'go/{slug}/')

    accounted = catalogue_slugs | set(registry.values())
    on_disk = {os.path.basename(p)[len('tour-'):-len('.html')]
               for p in glob.glob(os.path.join(root, 'tour-*.html'))}
    for slug in sorted(on_disk - accounted):
        print(f'WARNING: tour-{slug}.html exists but its slug is in neither the '
              f'resolved catalogue nor the slug registry; leaving it alone.')

    return removed


def lede_block(m, en, ja):
    """The description: first paragraph large, the rest reduced.

    Breaks where Bokun's description breaks. Bokun emits real paragraphs as <p>
    and uses <br> as editor spacing, and bokun_text drops the empty chunks a
    leading <br> produces, so the split matches the author's intent. A <br>
    placed mid-sentence would still split there, which is the honest limit of
    respecting the source layout.

    Japanese is paired by index because the two descriptions are split
    independently; where Japanese runs short the English paragraph stands in,
    which is the same fallback used for every other unreviewed field.
    """
    K = m['K']
    paras_en = m['lede_paras'][0] or ([m['lede'][0]] if m['lede'][0] else [])
    paras_ja = m['lede_paras'][1] or ([m['lede'][1]] if m['lede'][1] else [])
    out = []
    for i, text in enumerate(paras_en):
        key = f'{K}_lede' if i == 0 else f'{K}_lede_{i + 1}'
        en[key] = text
        ja[key] = paras_ja[i] if i < len(paras_ja) else text
        cls = 'lede' if i == 0 else 'lede-sub'
        out.append(f'        <p class="{cls}" data-i18n="{key}">{esc(text)}</p>')
    return '\n'.join(out)


def render_detail(m, tpl):
    en, ja = base_dict(m)
    slots = common_slots(m)
    slots['LEDE_BLOCK'] = lede_block(m, en, ja)
    slots['CHIPS_SECTION'] = chips_section(m, en, ja)
    slots['ROUTE_SECTION'] = route_section(m, en, ja)
    slots['OTHER_INFO_SECTION'] = other_info_section(m, en, ja)
    # The breakdown is unmounted, not deleted: it made the sticky booking
    # column ~150px taller for information that also lives in the widget.
    # Restoring it is passing price_breakdown_block(m, en, ja) again, and
    # where the two rates should live instead is still open.
    slots['WIDGET_BLOCK'] = widget_block(m)
    slots['DICT_SCRIPT'] = dict_script(en, ja)
    return render(tpl, slots)


def grid_region(models):
    """The tours-grid region: the cards, or an empty state when there are none.

    An empty catalogue is reachable and has happened -- every tour held back
    by the publish gates at once. Without this the page rendered its heading
    and lede, then two empty sections' worth of padding, then the bespoke
    CTA, which reads as broken rather than as deliberately empty. The
    filters section above collapses on its own (see tours.html: it hides
    when it holds no chip row); the home page shows the same line via
    home_tours_region.
    """
    if not models:
        return empty_state()
    return '\n\n'.join(card(m) for m in models)


def empty_state():
    """The one line of copy shown wherever tours would otherwise be listed."""
    return ('        <p class="tours-empty" data-i18n="tours_empty">New tours '
            'are in preparation. Please check back soon.</p>')


def home_tours_region(models):
    """The home page's tiles region, or the same empty state.

    The section is not hidden when empty: the hero's "Read more" link is
    href="#find", so collapsing the section would leave that anchor
    pointing at nothing.
    """
    if not models:
        return empty_state()
    return '\n\n'.join(tile(m) for m in models)


def card(m):
    """tours.html grid card."""
    K = m['K']
    price_html = ('' if not m['price_en'] else
                  f'<span class="price" data-i18n="{K}_price">{esc(m["price_en"])}</span>')
    return f'''        <a class="tcard" href="tour-{m['id']}.html" data-area="{m['area'].lower()}" data-themes="{' '.join(theme_slugs(m['themes']))}">
          <div class="pic" style="background-image: url('{esc(cover_at(m, 900))}')">
            <span class="num">No. {m['num']}</span>
          </div>
          <div class="t-body">
            <div class="t-meta"><span data-i18n="{area_key(m['area'])}">{m['area']}</span><span class="dot">・</span><span data-i18n="{LEN_KEY[m['length']]}">{m['length']}</span></div>
            <h3 data-i18n="{K}_name">{esc(m['title'][0])}</h3>
            <p class="t-sub" data-i18n="{K}_sub">{esc(m['sub'][0])}</p>
            <div class="t-foot"><span data-i18n="{K}_hours">{esc(m['hours'][0])}</span>{price_html}</div>
          </div>
        </a>'''


def tile(m):
    """index.html home tile."""
    K = m['K']
    return f'''        <a class="dest" href="tour-{m['id']}.html">
          <div class="ph">
            <div class="pic photo" style="background-image: url('{esc(cover_at(m, 900))}')"></div>
            <span class="num-tag">No. {m['num']}</span>
          </div>
          <div class="panel">
            <div class="t-meta"><span data-i18n="{area_key(m['area'])}">{m['area']}</span><span class="dot">・</span><span data-i18n="{LEN_KEY[m['length']]}">{m['length']}</span></div>
            <div class="name" data-i18n="{K}_name">{esc(m['title'][0])}</div>
            <p class="sub" data-i18n="{K}_sub">{esc(m['sub'][0])}</p>
            <div class="row"><span class="go"><span class="u" data-i18n="home_tours_cta">View this tour</span><span class="ar">&nbsp;→</span></span></div>
          </div>
        </a>'''


def rewrite_region(path, marker, content):
    s = open(path).read()
    start, end = f'<!-- CMS:{marker}:start -->', f'<!-- CMS:{marker}:end -->'
    i = s.index(start) + len(start)
    j = s.index(end)
    s = s[:i] + '\n\n' + content + '\n\n      ' + s[j:]
    open(path, 'w').write(s)
    return s


def set_page_dict(path, en, ja):
    s = open(path).read()
    line = dict_script(en, ja)
    if 'window.ZENRISE_CMS_DICT' in s:
        s = re.sub(r'<script>window\.ZENRISE_CMS_DICT = .*?;</script>', line, s, count=1, flags=re.S)
    else:
        s = s.replace('<script src="lang.js"></script>', line + '\n<script src="lang.js"></script>', 1)
    open(path, 'w').write(s)


def render_all(models, tpl, write=True):
    """Render every tour, holding back any that cannot be rendered.

    Returns (written, skipped) where skipped is [(slug, reason)].

    One misconfigured tour must not stop the site updating. area_key() and
    theme_slugs() raise BuildError on a value with no i18n key -- a tour in a
    city we have never had, for instance -- and this build runs unattended every
    hour, so an abort would freeze the whole site until someone noticed. The
    caller keeps the full `models` list for the stale-page cleanup, which must
    not delete the page of a tour that is merely misconfigured.
    """
    written, skipped = [], []
    for m in models:
        try:
            # Themes are validated here even though render_detail does not use
            # them: theme_slugs() is called later by card()/tile() for the grid,
            # which is outside this loop, so an invalid theme would otherwise
            # abort the build after these pages were already written. Validating
            # both here makes this the single gate, and everything downstream
            # runs on the tours this returns.
            theme_slugs(m['themes'])
            out = render_detail(m, tpl)
        except BuildError as e:
            skipped.append((m['id'], str(e)))
            continue
        name = f"tour-{m['id']}.html"
        if write:
            open(os.path.join(ROOT, name), 'w').write(out)
        written.append(name)
    return written, skipped


def main():
    source = 'bokun'
    if '--source' in sys.argv:
        try:
            source = sys.argv[sys.argv.index('--source') + 1]
        except IndexError:
            sys.exit('--source requires a value: bokun or cache')
    elif '--live' in sys.argv:
        source = 'bokun'          # retained alias, referenced by cms/tours-setup.md
    # --require-live: fail rather than quietly rebuild from the cache. The
    # scheduled workflow passes it, because a silent fallback there produces no
    # diff and so looks like a healthy run that published nothing.
    contents, cfg = fetch_tours(source, require_live='--require-live' in sys.argv)
    # STAGING ONLY: invented sample tours, appended from config. Production's
    # config has no sampleTours key, so nothing is appended there. They carry
    # their own bilingual copy and so are the only pages that can demonstrate a
    # fully Japanese tour while Bokun holds no Japanese.
    samples = cfg.get('sampleTours') or []
    if samples:
        print('NOTE: appending %d invented sample tour(s) — staging only: %s'
              % (len(samples), ', '.join(s['id'] for s in samples)))
        contents = list(contents) + samples

    models = [tour_model(a) for a in contents]

    # Display order follows the eyebrow number, never the order Bokun
    # happened to return the catalogue in. Without this the grid renders out
    # of sequence -- 02, 03, 01 -- because the Website product list's member
    # order is the client's to change and bears no relation to the numbering.
    # Unnumbered tours sort last rather than first.
    models.sort(key=lambda m: (m['num'] == '', m['num']))

    # Widget paths are configuration, not Bokun data, but they ride along inside
    # each cached record. Re-read them from config here so adding a widget takes
    # effect on a `--source cache` build instead of needing a live refetch.
    tours_cfg = cfg.get('tours') or {}
    # Derive the widget path when config has none. Bokun renders a calendar for
    # ANY product in the channel at
    #   <channel>/experience-calendar/<productId>
    # with no per-product setup in the panel -- verified against products that
    # have never had a widget configured. Without this a newly listed tour
    # published with "Booking widget not yet configured", which was the last
    # step still needing a developer.
    channel = (cfg.get('bookingChannelUUID') or '').strip()
    # Sample tours carry an invented bokunId, so deriving a widget URL for them
    # points at a product that does not exist. They are excluded by id.
    sample_ids = {s.get('id') for s in samples}
    for m in models:
        if str(m['bokun_id']) in tours_cfg:
            m['widgets'] = tours_cfg[str(m['bokun_id'])].get('widgets') or {}
        if (not (m.get('widgets') or {}).get('en') and channel
                and m.get('bokun_id') and m['id'] not in sample_ids):
            m['widgets'] = dict(m.get('widgets') or {},
                                en=f"{channel}/experience-calendar/{m['bokun_id']}")

    tpl_full = load_template('tour-detail.html')

    written, skipped = render_all(models, tpl_full)
    for slug, why in skipped:
        print(f'WARNING: held back {slug}: {why}')

    # Everything downstream -- the grid, the home tiles, the sitemap index and
    # the go/ redirects -- also calls area_key()/theme_slugs(), so a held-back
    # tour has to drop out of those too or it raises again there. `models` is
    # kept intact for the stale-page cleanup, which must not delete the page of
    # a tour that is only misconfigured.
    held = {slug for slug, _ in skipped}
    live = [m for m in models if m['id'] not in held]

    write_tours_index(live)
    go_written = write_go_redirects(live)

    # tours.html: filters + grid + card dict. The chips are built from `live`,
    # so a chip can never match nothing and a card can never be unreachable.
    rewrite_region(os.path.join(ROOT, 'tours.html'), 'tours-filters',
                   filter_rows(live))
    rewrite_region(os.path.join(ROOT, 'tours.html'), 'tours-grid',
                   grid_region(live))
    en, ja = {}, {}
    for m in live:
        e, j = base_dict(m)
        en.update(e); ja.update(j)
    set_page_dict(os.path.join(ROOT, 'tours.html'), en, ja)

    # index.html: featured tiles + dict (site-config order, else list order)
    featured_ids = [f['id'] if isinstance(f, dict) else f for f in (cfg.get('featuredTours') or [])]
    by_id = {m['id']: m for m in live}
    feats = [by_id[i] for i in featured_ids if i in by_id] or live
    rewrite_region(os.path.join(ROOT, 'index.html'), 'home-tours',
                   home_tours_region(feats))
    en, ja = {}, {}
    for m in feats:
        e, j = base_dict(m)
        en.update(e); ja.update(j)
    set_page_dict(os.path.join(ROOT, 'index.html'), en, ja)

    print(f'wrote {len(written)} tour page(s):', ', '.join(written))
    print('rewrote tours.html grid +', len(feats), 'home tiles')
    print(f'wrote {len(go_written)} go/ redirect(s):', ', '.join(go_written))

    # A tour dropping out of the resolved catalogue (spec 3.1) leaves a
    # registry-frozen slug with no page behind it any more; remove that
    # orphaned page and redirect so it stops being reachable.
    removed = cleanup_stale_pages(models)
    if removed:
        print(f'removed {len(removed)} stale page(s):', ', '.join(removed))
    else:
        print('removed 0 stale page(s)')


if __name__ == '__main__':
    main()
