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

PRICE = {
    'Half-day': {'key': 'booking_s2_half_price', 'en': '¥65,000 / group', 'ja': '¥65,000 ／ 1組'},
    'Full-day': {'key': 'booking_s2_full_price', 'en': '¥95,000 / group', 'ja': '¥95,000 ／ 1組'},
}
AREA_KEY = {'Kamakura': 'tours_area_kamakura', 'Enoshima': 'tours_area_enoshima', 'Yokohama': 'tours_area_yokohama'}
AREA_JA = {'Kamakura': '鎌倉', 'Enoshima': '江ノ島', 'Yokohama': '横浜'}
LEN_KEY = {'Half-day': 'tours_len_half', 'Full-day': 'tours_len_full'}
THEME_SLUG = {'Temples & Shrines': 'temples', 'Food': 'food', 'Walking': 'walking',
              'Views & Nature': 'nature', 'Local Life': 'local', 'Culture': 'culture'}


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


def tour_model(a, routes):
    m = {'id': a['id'], 'K': 'tours_' + a['id'], 'num': a['number']}
    for f in ('title', 'sub', 'hours', 'coverCaption', 'price', 'lede',
              'included', 'notIncluded', 'notAllowed', 'notSuitable'):
        m[f] = ((a.get(f + 'En') or '').strip(), (a.get(f + 'Ja') or '').strip())
    m['area'] = sel(a['area'])
    m['length'] = sel(a['length'])
    m['themes'] = a.get('themes') or []
    m['cover'] = (a.get('cover') or {}).get('url', '')
    p = PRICE[m['length']]
    m['price_key'] = None if m['price'][0] else p['key']
    m['price_en'] = m['price'][0] or p['en']
    m['price_ja'] = m['price'][1] or p['ja']
    m['route'] = routes.get(a['id'], [])
    m['full'] = bool(m['lede'][0])
    return m


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
    if m['price_key'] is None:
        en[K + '_price'] = m['price_en']
        ja[K + '_price'] = m['price_ja']
    return en, ja


def og_image(m):
    if not m['cover']:
        return f'{SITE}/assets/shrines/temple-gate-pine.jpg'
    return m['cover'] if m['cover'].startswith('http') else f"{SITE}/{m['cover']}"


def common_slots(m):
    lede_or_sub = m['lede'][0] or m['sub'][0]
    return {
        'ID': m['id'], 'K': m['K'], 'NUM': m['num'],
        'TITLE_EN': esc(m['title'][0]),
        'META_DESC': esc(f'{lede_or_sub} Private, 1–6 people, led by Zenrise.'),
        'OG_IMAGE': esc(og_image(m)),
        'COVER_URL': esc(m['cover']),
        'CAP_EN': esc(m['coverCaption'][0]),
        'AREA_KEY': AREA_KEY[m['area']], 'AREA_EN': m['area'],
        'LEN_KEY': LEN_KEY[m['length']], 'LEN_EN': m['length'],
        'HOURS_EN': esc(m['hours'][0]),
        'PRICE_KEY': m['price_key'] or (m['K'] + '_price'),
        'PRICE_EN': esc(m['price_en']),
        'CTA_EYEBROW_EN': esc(f"{m['price_en']} ・ 1–6 travelers"),
    }


def chips(m, field, prefix, en, ja):
    K = m['K']
    out = []
    for i, (e, j) in enumerate(zip(lines(m[field][0]), lines(m[field][1])), 1):
        en[f'{K}_{prefix}_{i}'] = e
        ja[f'{K}_{prefix}_{i}'] = j
        out.append(f'              <span class="chip" data-i18n="{K}_{prefix}_{i}">{esc(e)}</span>')
    return '\n'.join(out)


def route_rows(m, en, ja):
    K = m['K']
    rows = []
    for st in m['route']:
        n = st['n']
        en[f'{K}_rt_{n}_name'] = st['nameEn']; ja[f'{K}_rt_{n}_name'] = st['nameJa']
        en[f'{K}_rt_{n}_note'] = st['noteEn']; ja[f'{K}_rt_{n}_note'] = st['noteJa']
        rows.append(
            '        <div class="r-row">\n'
            f'          <div class="r-pic"><div class="stripes"></div><span class="rn">{n} · {esc(st["asset"])}</span></div>\n'
            f'          <div class="r-time">{st["time"]}</div>\n'
            f'          <div><h3 data-i18n="{K}_rt_{n}_name">{esc(st["nameEn"])}</h3>'
            f'<p class="r-note" data-i18n="{K}_rt_{n}_note">{esc(st["noteEn"])}</p></div>\n'
            f'          <div class="r-dist">{st["dist"]}</div>\n'
            '        </div>')
    return '\n'.join(rows)


def render_detail(m, tpl_full, tpl_prep):
    en, ja = base_dict(m)
    slots = common_slots(m)
    if m['full']:
        K = m['K']
        en[K + '_lede'] = m['lede'][0]; ja[K + '_lede'] = m['lede'][1]
        slots['LEDE_EN'] = esc(m['lede'][0])
        slots['CHIPS_INC'] = chips(m, 'included', 'inc', en, ja)
        slots['CHIPS_NINC'] = chips(m, 'notIncluded', 'ninc', en, ja)
        slots['CHIPS_NA'] = chips(m, 'notAllowed', 'na', en, ja)
        slots['CHIPS_NS'] = chips(m, 'notSuitable', 'ns', en, ja)
        slots['CAL_PRICE'] = m['price_en'].split(' / ')[0].split(' ／ ')[0]
        slots['ROUTE_ROWS'] = route_rows(m, en, ja)
        tpl = tpl_full
    else:
        tpl = tpl_prep
    slots['DICT_SCRIPT'] = dict_script(en, ja)
    return render(tpl, slots)


def card(m):
    """tours.html grid card."""
    K = m['K']
    return f'''        <a class="tcard" href="tour-{m['id']}.html" data-area="{m['area'].lower()}" data-themes="{' '.join(THEME_SLUG[t] for t in m['themes'])}">
          <div class="pic" style="background-image: url('{esc(m['cover'])}')">
            <span class="num">No. {m['num']}</span>
          </div>
          <div class="t-body">
            <div class="t-meta"><span data-i18n="{AREA_KEY[m['area']]}">{m['area']}</span><span class="dot">・</span><span data-i18n="{LEN_KEY[m['length']]}">{m['length']}</span></div>
            <h3 data-i18n="{K}_name">{esc(m['title'][0])}</h3>
            <p class="t-sub" data-i18n="{K}_sub">{esc(m['sub'][0])}</p>
            <div class="t-foot"><span data-i18n="{K}_hours">{esc(m['hours'][0])}</span><span class="price" data-i18n="{m['price_key'] or K + '_price'}">{esc(m['price_en'])}</span></div>
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
            <div class="t-meta"><span data-i18n="{AREA_KEY[m['area']]}">{m['area']}</span><span class="dot">・</span><span data-i18n="{LEN_KEY[m['length']]}">{m['length']}</span></div>
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
