#!/usr/bin/env python3
"""Render the tours section from the tours content model: one tour-<id>.html per
tour (full detail when a lede exists, otherwise the "in preparation" layout),
plus the card grid in tours.html and the tile grid in index.html (both between
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

import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = 'https://zenrise.jp'

class BuildError(Exception):
    pass


AREA_KEY = {'Kamakura': 'tours_area_kamakura', 'Enoshima': 'tours_area_enoshima', 'Yokohama': 'tours_area_yokohama'}
AREA_JA = {'Kamakura': '鎌倉', 'Enoshima': '江ノ島', 'Yokohama': '横浜'}
LEN_KEY = {'Half-day': 'tours_len_half', 'Full-day': 'tours_len_full'}
THEME_SLUG = {'Temples & Shrines': 'temples', 'Food': 'food', 'Walking': 'walking',
              'Views & Nature': 'nature', 'Local Life': 'local', 'Culture': 'culture',
              'Arts & Craft': 'arts'}


def theme_slugs(themes):
    out = []
    for t in themes:
        try:
            out.append(THEME_SLUG[t])
        except KeyError:
            raise BuildError(
                f'theme {t!r} has no slug. Add it to THEME_SLUG in build-tours.py '
                f'and to the filter buttons in tours.html, or correct the themes '
                f'value in cms/tours-config.json.')
    return out


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


def sel(v):
    """microCMS returns select values as lists; fixtures may use plain strings."""
    return v[0] if isinstance(v, list) else v


def lines(s):
    return [l.strip() for l in (s or '').splitlines() if l.strip()]


def fetch_tours(source):
    """Records + config. microCMS is no longer a tours source: Bokun is.

    See docs/superpowers/specs/2026-08-25-bokun-integration-design.md section 3.
    """
    sys.path.insert(0, os.path.dirname(HERE))
    from cms import tours_build_source
    records, cfg, warnings = tours_build_source.load_records(source)
    for w in warnings:
        print('WARNING:', w)
    return records, cfg


def tour_model(a):
    m = {'id': a['id'], 'K': 'tours_' + a['id'], 'num': a['number'],
         'bokun_id': a.get('bokunId'), 'widgets': a.get('widgets') or {},
         'price_rows': a.get('priceRows') or []}
    for f in ('title', 'sub', 'hours', 'coverCaption', 'price', 'lede',
              'included', 'notIncluded', 'notAllowed', 'notSuitable'):
        m[f] = ((a.get(f + 'En') or '').strip(), (a.get(f + 'Ja') or '').strip())
    m['area'] = a['area']
    m['length'] = a['length']
    m['themes'] = a.get('themes') or []
    m['cover'] = (a.get('cover') or {}).get('url', '')
    # Price is per tour and comes from Bokun, so there is no shared length key.
    m['price_key'] = None
    m['price_en'] = m['price'][0]
    m['price_ja'] = m['price'][1]
    m['route'] = a.get('route') or []
    # A tour is "full" when it has a price. Unpriced products get the
    # in-preparation layout (spec 3.5).
    m['full'] = bool(m['price'][0])
    return m


def meta_desc(m):
    text = m['sub'][0] or m['lede'][0] or f"{m['title'][0]} — a Zenrise private experience."
    if len(text) <= 160:
        return text
    cut = text[:160].rsplit(' ', 1)[0]
    return cut.rstrip(' ,.;:') + '…'


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
        data['image'] = m['cover']
    rows = m.get('price_rows') or []
    if m['full'] and rows:
        low = min(rows, key=lambda r: r['amount'])
        data['offers'] = {
            '@type': 'Offer',
            'price': low['amount'],
            'priceCurrency': low['currency'],
            'availability': 'https://schema.org/InStock',
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


def base_dict(m):
    """Keys shared by every rendering of this tour (cards, tiles, detail head)."""
    K = m['K']
    en = {K + '_name': m['title'][0], K + '_sub': m['sub'][0], K + '_hours': m['hours'][0],
          K + '_title': f"{m['title'][0]} — Zenrise",
          K + '_eyebrow': f"Tour No. {m['num']}",
          K + '_cap': m['coverCaption'][0],
          K + '_cta_eyebrow': f"{m['price_en']} ・ 1–6 travelers"}
    ja = {K + '_name': m['title'][1], K + '_sub': m['sub'][1], K + '_hours': m['hours'][1],
          K + '_title': f"{m['title'][1]} — Zenrise",
          K + '_eyebrow': f"ツアー No. {m['num']}",
          K + '_cap': m['coverCaption'][1],
          K + '_cta_eyebrow': f"{m['price_ja']} ・ 1〜6名"}
    en[K + '_price'] = m['price_en']
    ja[K + '_price'] = m['price_ja']
    return en, ja


def og_image(m):
    if not m['cover']:
        return f'{SITE}/assets/shrines/temple-gate-pine.jpg'
    return m['cover'] if m['cover'].startswith('http') else f"{SITE}/{m['cover']}"


def common_slots(m):
    return {
        'ID': m['id'], 'K': m['K'], 'NUM': m['num'],
        'TITLE_EN': esc(m['title'][0]),
        'META_DESC': esc(meta_desc(m)),
        'JSON_LD': json_ld(m),
        'OG_IMAGE': esc(og_image(m)),
        'COVER_URL': esc(m['cover']),
        'CAP_EN': esc(m['coverCaption'][0]),
        'AREA_KEY': area_key(m['area']), 'AREA_EN': m['area'],
        'LEN_KEY': LEN_KEY[m['length']], 'LEN_EN': m['length'],
        'HOURS_EN': esc(m['hours'][0]),
        'PRICE_KEY': m['price_key'] or (m['K'] + '_price'),
        'PRICE_EN': esc(m['price_en']),
        'CTA_EYEBROW_EN': esc(f"{m['price_en']} ・ 1–6 travelers"),
        'WIDGET_BLOCK': '', 'CHIPS_SECTION': '', 'ROUTE_SECTION': '',
    }


def chips(m, field, prefix, en, ja):
    if not m[field][0]:
        return ''
    K = m['K']
    out = []
    for i, (e, j) in enumerate(zip(lines(m[field][0]), lines(m[field][1])), 1):
        en[f'{K}_{prefix}_{i}'] = e
        ja[f'{K}_{prefix}_{i}'] = j
        out.append(f'              <span class="chip" data-i18n="{K}_{prefix}_{i}">{esc(e)}</span>')
    return '\n'.join(out)


CHIP_GROUPS = (('included', 'inc', 'td_included', 'Included'),
               ('notIncluded', 'ninc', 'td_notinc', 'Not included'),
               ('notAllowed', 'na', 'td_notallowed', 'Not allowed'),
               ('notSuitable', 'ns', 'td_notsuitable', 'Not suitable for'))


def chips_section(m, en, ja):
    """The whole chip-groups block, or nothing.

    Bokun has no inclusions field. Only tours whose description carries an inline
    list get chips at all, so the labelled groups must not render empty. See spec
    3.4 and 3.4.1.
    """
    groups = []
    for field, prefix, key, label in CHIP_GROUPS:
        body = chips(m, field, prefix, en, ja)
        if not body.strip():
            continue
        groups.append(
            '          <div class="grp">\n'
            f'            <span class="label" data-i18n="{key}">{label}</span>\n'
            '            <div class="chips">\n'
            f'{body}\n'
            '            </div>\n'
            '          </div>')
    if not groups:
        return ''
    return ('        <div class="chip-groups">\n'
            + '\n'.join(groups)
            + '\n        </div>')


# A stop duration written at the head of the body, e.g. "30min The history of…".
# Only some products carry these, so the time cell is optional per row.
_STOP_TIME = re.compile(
    r'^\s*(\d+\s*(?:min|mins|minute|minutes|hr|hrs|hour|hours))\b[\s:·\-–—]*',
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
        en[f'{K}_rt_{n}_name'] = st['title']; ja[f'{K}_rt_{n}_name'] = st['title']
        en[f'{K}_rt_{n}_note'] = body;        ja[f'{K}_rt_{n}_note'] = body
        time_cell = f'<div class="r-time">{esc(time)}</div>' if time else ''
        rows.append(
            f'        <div class="r-row{"" if time else " no-time"}">\n'
            f'          <div class="r-num">{n}</div>\n'
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


def widget_block(m):
    """Bokun calendar widget mount for a priced tour.

    The widget is a cross-origin iframe, so it cannot inherit our CSS or the
    Adobe kit; colour is configured in Bokun's panel. See spec section 3.6.
    """
    if not m['full']:
        return ''
    widgets = m.get('widgets') or {}
    en = widgets.get('en')
    if not en:
        return (f'        <aside class="cal-missing" id="book" data-widget-missing="{m["id"]}">\n'
                f'          <p>Booking widget not yet configured for this tour.</p>\n'
                f'        </aside>')
    channel = en.split('/')[0]
    src = f'{WIDGET_HOST}/online-sales/{en}'
    ja = widgets.get('ja')
    ja_attr = f' data-widget-ja="{WIDGET_HOST}/online-sales/{ja}"' if ja and ja != en else ''
    return f'''        <aside class="cal" id="book" data-screen-label="07 Tour detail — Booking">
          <script type="text/javascript" src="{WIDGET_LOADER}{channel}" async></script>
          <div class="bokunWidget" data-src="{src}"{ja_attr}></div>
          <noscript><a class="c-go" href="go/{m['id']}/">Book this experience&nbsp;&nbsp;→</a></noscript>
        </aside>'''


def render_detail(m, tpl_full, tpl_prep):
    en, ja = base_dict(m)
    slots = common_slots(m)
    if m['full']:
        K = m['K']
        en[K + '_lede'] = m['lede'][0]; ja[K + '_lede'] = m['lede'][1]
        slots['LEDE_EN'] = esc(m['lede'][0])
        slots['CHIPS_SECTION'] = chips_section(m, en, ja)
        slots['PRICE_ROWS'] = '\n'.join(
            f'          <li>{esc(r)}</li>' for r in _price_lines(m))
        slots['ROUTE_SECTION'] = route_section(m, en, ja)
        slots['WIDGET_BLOCK'] = widget_block(m)
        tpl = tpl_full
    else:
        tpl = tpl_prep
    slots['DICT_SCRIPT'] = dict_script(en, ja)
    return render(tpl, slots)


def _price_lines(m):
    sys.path.insert(0, os.path.dirname(HERE))
    from cms import bokun_price
    return bokun_price.format_full(m['price_rows'], 'en')


def card(m):
    """tours.html grid card."""
    K = m['K']
    price_html = ('' if not m['price_en'] else
                  f'<span class="price" data-i18n="{K}_price">{esc(m["price_en"])}</span>')
    return f'''        <a class="tcard" href="tour-{m['id']}.html" data-area="{m['area'].lower()}" data-themes="{' '.join(theme_slugs(m['themes']))}">
          <div class="pic" style="background-image: url('{esc(m['cover'])}')">
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
            <div class="pic photo" style="background-image: url('{esc(m['cover'])}')"></div>
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


def main():
    source = 'bokun'
    if '--source' in sys.argv:
        try:
            source = sys.argv[sys.argv.index('--source') + 1]
        except IndexError:
            sys.exit('--source requires a value: bokun or cache')
    elif '--live' in sys.argv:
        source = 'bokun'          # retained alias, referenced by cms/tours-setup.md
    contents, cfg = fetch_tours(source)
    models = [tour_model(a) for a in contents]

    tpl_full = load_template('tour-detail.html')
    tpl_prep = load_template('tour-prep.html')

    written = []
    for m in models:
        out = render_detail(m, tpl_full, tpl_prep)
        name = f"tour-{m['id']}.html"
        open(os.path.join(ROOT, name), 'w').write(out)
        written.append(name + ('' if m['full'] else ' (prep)'))

    write_tours_index(models)

    # tours.html: grid + card dict
    rewrite_region(os.path.join(ROOT, 'tours.html'), 'tours-grid',
                   '\n\n'.join(card(m) for m in models))
    en, ja = {}, {}
    for m in models:
        e, j = base_dict(m)
        en.update(e); ja.update(j)
    set_page_dict(os.path.join(ROOT, 'tours.html'), en, ja)

    # index.html: featured tiles + dict (site-config order, else list order)
    featured_ids = [f['id'] if isinstance(f, dict) else f for f in (cfg.get('featuredTours') or [])]
    by_id = {m['id']: m for m in models}
    feats = [by_id[i] for i in featured_ids if i in by_id] or models
    rewrite_region(os.path.join(ROOT, 'index.html'), 'home-tours',
                   '\n\n'.join(tile(m) for m in feats))
    en, ja = {}, {}
    for m in feats:
        e, j = base_dict(m)
        en.update(e); ja.update(j)
    set_page_dict(os.path.join(ROOT, 'index.html'), en, ja)

    print(f'wrote {len(written)} tour page(s):', ', '.join(written))
    print('rewrote tours.html grid +', len(feats), 'home tiles')


if __name__ == '__main__':
    main()
