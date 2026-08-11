#!/usr/bin/env python3
"""Render the news section (news.html, news-<slug>.html, sitemap.xml) from microCMS.

Stdlib only — runs locally and in GitHub Actions. Credentials come from
MICROCMS_SERVICE_ID / MICROCMS_API_KEY env vars, falling back to cms/.env.

Templates in cms/templates/ are derived from the hand-built pages; static
chrome (CSS, nav, footer, fit script) lives there. Site-wide design changes
must be applied to the templates as well as the other pages.

Body HTML from microCMS's rich editor is normalized by them: h2 carries an id,
images arrive as <figure><img src width height alt></figure>. Sections are
delimited by h2; portrait images (height > width) get the tall slot; the
figcaption is the image's alt text. EN markup drives the page structure and
JA text is mapped onto it positionally, so both bodies should keep the same
shape (same sections, images in the same places). Either language may be
left empty — the other fills in.
"""
import json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = 'https://zenrise.jp'
IMG_PAGE = '?fm=webp&q=82&w=1920'   # article hero
IMG_FIG = '?fm=webp&q=82&w=1600'    # in-article figures, featured card
IMG_CARD = '?fm=webp&q=82&w=1200'   # index grid cards
IMG_OG = '?fm=jpg&w=1200'           # link previews: JPG for scraper compatibility

STATIC_PAGES = ['', 'about.html', 'contact.html', 'terms.html', 'news.html']


def env(name):
    v = os.environ.get(name)
    if v:
        return v
    try:
        for line in open(os.path.join(HERE, '.env')):
            line = line.strip()
            if line.startswith(name + '='):
                return line.split('=', 1)[1].strip()
    except FileNotFoundError:
        pass
    sys.exit(f'missing {name} (env var or cms/.env)')


def fetch_articles():
    service, key = env('MICROCMS_SERVICE_ID'), env('MICROCMS_API_KEY')
    req = urllib.request.Request(
        f'https://{service}.microcms.io/api/v1/news?limit=100&orders=-date',
        headers={'X-MICROCMS-API-KEY': key})
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    return data['contents']


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))


def text_html(s):
    """textArea field → HTML: escape, newlines become <br>."""
    return esc(s.replace('\r\n', '\n').replace('\r', '\n').strip()).replace('\n', '<br>')


BLOCK_RE = re.compile(r'<(h2|h3|p|figure|ul|ol|blockquote)\b[^>]*>(.*?)</\1>', re.S)
IMG_RE = re.compile(r'<img\b[^>]*>')
ATTR_RE = r'\b{}="([^"]*)"'


def img_attrs(tag):
    def a(name, default=''):
        m = re.search(ATTR_RE.format(name), tag)
        return m.group(1) if m else default
    try:
        w, h = int(a('width', '0')), int(a('height', '0'))
    except ValueError:
        w = h = 0
    return {'src': a('src'), 'alt': a('alt'), 'w': w, 'h': h}


def parse_body(html):
    """Rich-editor HTML → [{'h': inner|None, 'blocks': [('fig',{..})|('p',inner)]}]."""
    sections = []
    cur = {'h': None, 'blocks': []}
    for m in BLOCK_RE.finditer(html or ''):
        tag, inner = m.group(1), m.group(2).strip()
        if tag == 'h2':
            if cur['h'] is not None or cur['blocks']:
                sections.append(cur)
            cur = {'h': inner, 'blocks': []}
        elif tag == 'figure':
            for img in IMG_RE.findall(m.group(0)):
                cur['blocks'].append(('fig', img_attrs(img)))
        else:
            if not re.sub(r'<br\s*/?>|&nbsp;|\s', '', inner):
                continue  # editor leaves empty <p><br></p> paragraphs behind
            if tag != 'p':
                inner = m.group(0)  # pass lists/quotes through whole
            cur['blocks'].append(('p', inner))
    if cur['h'] is not None or cur['blocks']:
        sections.append(cur)
    return sections


def pick(a, key):
    """Field pair → (en_value, ja_value), either side falling back to the other."""
    en, ja = (a.get(key + 'En') or '').strip(), (a.get(key + 'Ja') or '').strip()
    return en or ja, ja or en


def first_sentence(s, lang):
    s = s.strip()
    if not s:
        return ''
    if lang == 'ja':
        return s.split('。')[0] + '。' if '。' in s else s
    head = s.split('. ')[0]
    return head if head == s else head + '.'


def load_template(name):
    return open(os.path.join(HERE, 'templates', name)).read()


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


def article_model(a):
    """Normalize one API entry into everything the templates need."""
    m = {'id': a['id'], 'key': 'cms_' + a['id'], 'date': a['date'][:10].replace('-', '.'),
         'iso': a['date'][:10]}
    for f in ('title', 'subtitle', 'excerpt', 'lead', 'closingHeading',
              'closingBody', 'note', 'outro'):
        m[f] = pick(a, f)
    if not m['excerpt'][0]:
        m['excerpt'] = (first_sentence(m['lead'][0], 'en'),
                        first_sentence(m['lead'][1], 'ja'))
    m['hero'] = (a.get('hero') or {}).get('url', '')
    body_en = parse_body(a.get('bodyEn') or '')
    body_ja = parse_body(a.get('bodyJa') or '')
    m['sections'] = body_en or body_ja
    m['sections_ja'] = body_ja or body_en
    return m


def render_article(m, num, tpl):
    K = m['key']
    en, ja = {}, {}

    def put(suffix, pair):
        en[K + suffix], ja[K + suffix] = pair

    put('_page_title', (f"{m['title'][0]} — Zenrise News",
                        f"{m['title'][1]} — Zenrise ニュース"))
    put('_title', m['title'])

    sub_line = ''
    if m['subtitle'][0]:
        put('_subtitle', m['subtitle'])
        sub_line = f'        <p class="sub" data-i18n="{K}_subtitle">{esc(m["subtitle"][0])}</p>\n'

    lead_line = ''
    if m['lead'][0]:
        put('_lead', (text_html(m['lead'][0]), text_html(m['lead'][1])))
        lead_line = f'        <p class="lead" data-i18n-html="{K}_lead">{en[K + "_lead"]}</p>'

    # ── numbered sections, JA mapped positionally ──
    out = []
    for i, sec in enumerate(m['sections'], 1):
        sj = m['sections_ja'][i - 1] if i - 1 < len(m['sections_ja']) else {'h': None, 'blocks': []}
        figs_ja = [b for t, b in sj['blocks'] if t == 'fig']
        ps_ja = [b for t, b in sj['blocks'] if t == 'p']
        lines = ['        <section class="sec">',
                 f'          <span class="sec-label">{i:02d}</span>']
        if sec['h'] is not None:
            put(f'_s{i}_h', (sec['h'], sj['h'] if sj['h'] is not None else sec['h']))
            lines.append(f'          <h2 data-i18n-html="{K}_s{i}_h">{sec["h"]}</h2>')
        nf = np = 0
        for t, b in sec['blocks']:
            if t == 'fig':
                nf += 1
                tall = ' tall' if b['h'] > b['w'] else ''
                lines.append('          <figure class="fig">')
                lines.append(f'''            <div class="ph{tall}" style="background-image: url('{esc(b["src"] + IMG_FIG)}')"></div>''')
                if b['alt']:
                    alt_ja = figs_ja[nf - 1]['alt'] if nf - 1 < len(figs_ja) else ''
                    put(f'_s{i}_f{nf}_cap', (b['alt'], alt_ja or b['alt']))
                    lines.append(f'            <figcaption data-i18n="{K}_s{i}_f{nf}_cap">{esc(b["alt"])}</figcaption>')
                lines.append('          </figure>')
            else:
                np += 1
                p_ja = ps_ja[np - 1] if np - 1 < len(ps_ja) else b
                put(f'_s{i}_p{np}', (b, p_ja))
                lines.append(f'          <p data-i18n-html="{K}_s{i}_p{np}">{b}</p>')
        lines.append('        </section>')
        out.append('\n'.join(lines))

    if m['closingHeading'][0] or m['closingBody'][0]:
        lines = ['        <section class="sec">']
        if m['closingHeading'][0]:
            put('_closing_h', m['closingHeading'])
            lines.append(f'          <h2 data-i18n="{K}_closing_h">{esc(m["closingHeading"][0])}</h2>')
        if m['closingBody'][0]:
            put('_closing_p', (text_html(m['closingBody'][0]), text_html(m['closingBody'][1])))
            lines.append(f'          <p data-i18n-html="{K}_closing_p">{en[K + "_closing_p"]}</p>')
        lines.append('        </section>')
        out.append('\n'.join(lines))

    sections = '\n\n'.join(out)

    # ── CTA panel: our own tours (Viator/OTA panel removed 2026-08 — premium
    # brand split; articles are destination content, booking CTAs stay ours) ──
    panels = []
    if m['outro'][0]:
        put('_outro', (text_html(m['outro'][0]), text_html(m['outro'][1])))
        panels.append(
            '          <aside class="cta-panel outline">\n'
            '            <span class="cp-label" data-i18n="art_cta_ours">Our own tours</span>\n'
            f'            <p data-i18n-html="{K}_outro">{en[K + "_outro"]}</p>\n'
            '            <a class="cta" href="about.html">'
            '<span class="u" data-i18n="art_outro_cta">About our tours</span><span class="ar">→</span></a>\n'
            '          </aside>')
    cta = ''
    if panels:
        cta = '\n        <div class="cta-duo">\n' + '\n'.join(panels) + '\n        </div>\n'

    url = f'{SITE}/news-{m["id"]}.html'
    og_title = m['title'][0] + (f' — {m["subtitle"][0]}' if m['subtitle'][0] else '')
    hero_style = ''
    if m['hero']:
        hero_style = f''' style="background-image: url('{esc(m["hero"] + IMG_PAGE)}')"'''

    og_image = m['hero'] + IMG_OG if m['hero'] else f'{SITE}/assets/shrines/temple-gate-pine.jpg'
    json_ld = '<script type="application/ld+json">\n' + json.dumps({
        '@context': 'https://schema.org',
        '@type': 'Article',
        'headline': m['title'][0],
        'description': m['excerpt'][0],
        'datePublished': m['iso'],
        'image': og_image,
        'mainEntityOfPage': url,
        'author': {'@type': 'Organization', 'name': 'Zenrise', 'url': f'{SITE}/'},
        'publisher': {'@type': 'Organization', 'name': 'Zenrise', 'url': f'{SITE}/',
                      'logo': {'@type': 'ImageObject', 'url': f'{SITE}/favicon-512.png'}},
    }, ensure_ascii=False, indent=2).replace('</', '<\\/') + '\n</script>'

    return render(tpl, {
        'META_DESC': esc(m['excerpt'][0]),
        'CANONICAL_URL': url,
        'OG_TITLE': esc(og_title),
        'OG_DESC': esc(m['excerpt'][0]),
        'OG_IMAGE': esc(og_image),
        'JSON_LD': json_ld,
        'K': K,
        'PAGE_TITLE': esc(en[K + '_page_title']),
        'NUM': f'{num:02d}',
        'DATE': m['date'],
        'TITLE': esc(m['title'][0]),
        'SUBTITLE_LINE': sub_line,
        'HERO_STYLE': hero_style,
        'LEAD_LINE': lead_line,
        'SECTIONS': sections,
        'CTA': cta,
        'DICT_SCRIPT': dict_script(en, ja),
    })


INDEX_PAGE_SIZE = 7  # articles per pagination page: 1 featured + 6 cards


def render_index(models, tpl):
    """Render the index as .news-page containers (featured + card grid per
    page); the template's pager script toggles them, so each page leads with
    its own featured article. All but the first start hidden."""
    en, ja = {}, {}

    def put(key, pair):
        en[key], ja[key] = pair

    for m in models:
        put(m['key'] + '_title', m['title'])
        if m['subtitle'][0]:
            put(m['key'] + '_subtitle', m['subtitle'])

    def featured_html(m):
        K = m['key']
        put(K + '_excerpt', (text_html(m['excerpt'][0]), text_html(m['excerpt'][1])))
        sub = ''
        if m['subtitle'][0]:
            sub = f'          <p class="sub" data-i18n="{K}_subtitle">{esc(m["subtitle"][0])}</p>\n'
        photo = f''' style="background-image: url('{esc(m["hero"] + IMG_FIG)}')"''' if m['hero'] else ''
        return (
            f'      <a class="featured intro-b" href="news-{m["id"]}.html">\n'
            f'        <div class="f-photo"{photo}></div>\n'
            '        <div class="f-body">\n'
            '          <div class="f-meta">\n'
            f'            <span>{m["date"]}</span>\n'
            '          </div>\n'
            f'          <h2 data-i18n="{K}_title">{esc(m["title"][0])}</h2>\n'
            + sub +
            f'          <p class="excerpt" data-i18n-html="{K}_excerpt">{en[K + "_excerpt"]}</p>\n'
            '          <span class="more"><span data-i18n="news_read">Read article</span><span class="ar">&nbsp;→</span></span>\n'
            '        </div>\n'
            '      </a>\n')

    def card_html(m):
        K = m['key']
        sub = ''
        if m['subtitle'][0]:
            sub = f'          <p class="c-sub" data-i18n="{K}_subtitle">{esc(m["subtitle"][0])}</p>\n'
        pic = f''' style="background-image: url('{esc(m["hero"] + IMG_CARD)}')"''' if m['hero'] else ''
        return (
            f'        <a class="card" href="news-{m["id"]}.html">\n'
            f'          <div class="pic"{pic}></div>\n'
            f'          <div class="c-meta"><span>{m["date"]}</span></div>\n'
            f'          <h3 data-i18n="{K}_title">{esc(m["title"][0])}</h3>\n'
            + sub +
            '        </a>\n')

    pages = []
    for start in range(0, len(models), INDEX_PAGE_SIZE):
        chunk = models[start:start + INDEX_PAGE_SIZE]
        block = f'      <div class="news-page"{" hidden" if start else ""}>\n'
        block += featured_html(chunk[0])
        if len(chunk) > 1:
            block += '      <div class="news-grid">\n'
            block += ''.join(card_html(m) for m in chunk[1:])
            block += '      </div>\n'
        block += '      </div>\n'
        pages.append(block)

    return render(tpl, {
        'PAGES': ''.join(pages),
        'DICT_SCRIPT': dict_script(en, ja),
    })


def render_sitemap(models):
    urls = [f'{SITE}/{p}' for p in STATIC_PAGES]
    urls += [f'{SITE}/news-{m["id"]}.html' for m in models]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines += [f'  <url><loc>{u}</loc></url>' for u in urls]
    lines.append('</urlset>')
    return '\n'.join(lines) + '\n'


def main():
    articles = fetch_articles()
    if not articles:
        print('WARNING: microCMS returned 0 published articles; writing empty index')
    models = [article_model(a) for a in articles]

    art_tpl = load_template('article.html')
    written = []
    for i, m in enumerate(models):
        path = os.path.join(ROOT, f'news-{m["id"]}.html')
        open(path, 'w').write(render_article(m, 6 + i, art_tpl))
        written.append(os.path.basename(path))

    open(os.path.join(ROOT, 'news.html'), 'w').write(
        render_index(models, load_template('news-index.html')))
    open(os.path.join(ROOT, 'sitemap.xml'), 'w').write(render_sitemap(models))

    stale = [f for f in os.listdir(ROOT)
             if re.fullmatch(r'news-[A-Za-z0-9_-]+\.html', f) and f not in written]
    for f in stale:
        os.remove(os.path.join(ROOT, f))
        print('removed stale page:', f)

    print(f'wrote news.html, sitemap.xml and {len(written)} article page(s):',
          ', '.join(written))


if __name__ == '__main__':
    main()
