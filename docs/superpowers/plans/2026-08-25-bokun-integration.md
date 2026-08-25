# Bokun Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate the site's tour pages, tours grid and homepage tiles from the client's Bokun account, with booking handled by embedded Bokun widgets.

**Architecture:** A new data layer (`cms/bokun_*.py`) fetches the Zenrise-tier products from Bokun's native REST API and emits records in the *same shape* as the existing `cms/tours-fixture.json` entries. That keeps `tour_model()` and every downstream renderer in `cms/build-tours.py` as the stable seam, so the change is a new source plus targeted edits, not a rewrite. Everything is offline-testable: the HTTP transport is injected, and tests run against recorded Bokun responses.

**Tech Stack:** Python 3 standard library only (`urllib`, `hmac`, `hashlib`, `html`, `json`, `unittest`). No new dependencies — the repo has no package manifest and the GitHub Action must stay dependency-free. Static HTML + vanilla JS site, no build step beyond these scripts.

**Spec:** `docs/superpowers/specs/2026-08-25-bokun-integration-design.md`

## Global Constraints

- **Staging only.** Nothing in this plan ships to zenrise.jp. `zenrise-staging` repo throughout.
- **Out of scope, do not modify:** `contact.html`, `datepicker.js`, `relay/`, `archive/`.
- **Never render OTA-tier products.** Catalogue resolution must fail loudly rather than fall back to all products. The seven OTA products are ids `1272734, 1272756, 1272817, 1272825, 1272835, 1272849, 1273963`.
- **The four Zenrise-tier product ids:** `1273232` (Ikebana), `1273235` (candle-making), `1273194` (The Zen Journey), `1275339` (Swordsmithing).
- **Credentials** live in `~/.bokun-api.env` (`BOKUN_ACCESS_KEY`, `BOKUN_SECRET_KEY`, `BOKUN_OCTO_KEY`). Never read them into logs, test fixtures, commit messages, or generated HTML.
- **API base:** `https://api.bokun.io`. Auth: `X-Bokun-AccessKey`, `X-Bokun-Date` (UTC `%Y-%m-%d %H:%M:%S`), `X-Bokun-Signature` = base64(HMAC-SHA1(secret, date + accessKey + method + path)).
- **Site palette** for any generated styling: `--ink #294138`, `--bg #F7F4EA`, hover `#1F3328`, panel `#EDE9E5`.
- **Availability is never fetched to render a calendar** — only to derive prices. The widget owns availability.
- **Tests:** stdlib `unittest`, run with `python3 -m unittest discover -s cms/tests -t .` from the repo root. No network in tests.
- **Commit style:** imperative subject, body explaining why. End every commit message with:
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`

---

# Phase 1 — Data layer

Offline-testable. Produces records; touches no HTML.

### Task 1: Config file and loader

**Files:**
- Create: `cms/tours-config.json`
- Create: `cms/tours_config.py`
- Create: `cms/tests/__init__.py` (empty)
- Test: `cms/tests/test_tours_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `ConfigError(Exception)`
  - `load(path: str | None = None) -> dict` — defaults to `cms/tours-config.json`
  - `catalogue_ids(cfg: dict) -> list[int]` — raises `ConfigError` if empty
  - `tour_entry(cfg: dict, bokun_id: int) -> dict` — raises `ConfigError` if absent or missing `slug`
  - `corrections(cfg: dict) -> dict[str, str]`

- [ ] **Step 1: Write the failing test**

```python
# cms/tests/test_tours_config.py
import json, os, tempfile, unittest
from cms import tours_config


def write(tmp, data):
    p = os.path.join(tmp, 'c.json')
    with open(p, 'w') as f:
        json.dump(data, f)
    return p


class TestLoad(unittest.TestCase):
    def test_catalogue_ids_returns_allowlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tours_config.load(write(tmp, {'allowlist': [1273232, 1273235], 'tours': {}}))
            self.assertEqual(tours_config.catalogue_ids(cfg), [1273232, 1273235])

    def test_empty_allowlist_is_an_error_not_a_wildcard(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tours_config.load(write(tmp, {'allowlist': [], 'tours': {}}))
            with self.assertRaises(tours_config.ConfigError):
                tours_config.catalogue_ids(cfg)

    def test_tour_entry_found_by_int_or_str_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tours_config.load(write(tmp, {
                'allowlist': [1273232],
                'tours': {'1273232': {'slug': 'ikebana-ichigo-ichie', 'number': '01'}}}))
            self.assertEqual(tours_config.tour_entry(cfg, 1273232)['slug'], 'ikebana-ichigo-ichie')

    def test_missing_tour_entry_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tours_config.load(write(tmp, {'allowlist': [999], 'tours': {}}))
            with self.assertRaises(tours_config.ConfigError):
                tours_config.tour_entry(cfg, 999)

    def test_entry_without_slug_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tours_config.load(write(tmp, {'allowlist': [1], 'tours': {'1': {'number': '01'}}}))
            with self.assertRaises(tours_config.ConfigError):
                tours_config.tour_entry(cfg, 1)

    def test_corrections_defaults_to_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tours_config.load(write(tmp, {'allowlist': [1], 'tours': {}}))
            self.assertEqual(tours_config.corrections(cfg), {})


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/projects/zenrise-staging && python3 -m unittest discover -s cms/tests -t . -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cms.tours_config'`

Note: `cms/` needs to be an importable package. Create `cms/__init__.py` (empty) in Step 3 if it does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# cms/tours_config.py
"""Everything the tours build needs that Bokun cannot express.

Bokun has no slug, no tour number, and unreliable categories, so those are
pinned by hand here. See docs/superpowers/specs/2026-08-25-bokun-integration-design.md
section 3.9.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(HERE, 'tours-config.json')


class ConfigError(Exception):
    pass


def load(path=None):
    with open(path or DEFAULT_PATH) as f:
        return json.load(f)


def catalogue_ids(cfg):
    ids = cfg.get('allowlist') or []
    if not ids:
        raise ConfigError(
            'allowlist is empty and no product list resolved. Refusing to build: '
            'an empty catalogue must never mean "render every Bokun product", '
            'because that would publish the OTA-tier tours.')
    return [int(i) for i in ids]


def tour_entry(cfg, bokun_id):
    tours = cfg.get('tours') or {}
    entry = tours.get(str(bokun_id)) or tours.get(bokun_id)
    if entry is None:
        raise ConfigError(
            f'Bokun product {bokun_id} is in the catalogue but has no entry in '
            f'tours-config.json. Add one with a permanent slug before building; '
            f'deriving a slug from the title would make the URL churn.')
    if not entry.get('slug'):
        raise ConfigError(f'tours-config.json entry for {bokun_id} has no slug.')
    return entry


def corrections(cfg):
    return cfg.get('corrections') or {}
```

```json
{
  "productListName": "Website",
  "allowlist": [1273232, 1273235, 1273194, 1275339],
  "corrections": {
    "passag e through": "passage through",
    "templ e grounds": "temple grounds",
    "templ e cuisine": "temple cuisine",
    "wa l ked": "walked"
  },
  "tours": {
    "1273232": {
      "slug": "ikebana-ichigo-ichie",
      "number": "01",
      "area": "Kamakura",
      "length": "Half-day",
      "themes": ["Arts & Craft"],
      "jaReviewed": false,
      "widgets": {}
    },
    "1273235": {
      "slug": "candle-making",
      "number": "02",
      "area": "Kamakura",
      "length": "Half-day",
      "themes": ["Arts & Craft"],
      "jaReviewed": false,
      "widgets": {}
    },
    "1273194": {
      "slug": "zen-journey",
      "number": "03",
      "area": "Kamakura",
      "length": "Half-day",
      "themes": ["Temples & Shrines", "Walking"],
      "jaReviewed": false,
      "widgets": {}
    },
    "1275339": {
      "slug": "swordsmithing",
      "number": "04",
      "area": "Kamakura",
      "length": "Half-day",
      "themes": ["Arts & Craft"],
      "jaReviewed": false,
      "widgets": {}
    }
  }
}
```

Note on `themes`: `"Arts & Craft"` is a new theme value not in `build-tours.py`'s `THEME_SLUG`. Task 7 extends that map. Do not invent other theme strings.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest discover -s cms/tests -t . -v`
Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add cms/__init__.py cms/tours_config.py cms/tours-config.json cms/tests/__init__.py cms/tests/test_tours_config.py
git commit -m "Add tours config: the inputs Bokun cannot express

Slug, tour number, filter values and widget paths are pinned by hand because
Bokun has no slug field, deriving one from the title would churn URLs, and
activityCategories exists on only two of the four tier products.

catalogue_ids() raises rather than returning an empty list, so a failed product
list resolution can never be read as 'render everything' and publish the OTA
tours.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Text normalisation

**Files:**
- Create: `cms/bokun_text.py`
- Test: `cms/tests/test_bokun_text.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `clean(raw: str, corrections: dict | None = None) -> tuple[str, list[str]]` — returns cleaned single-line text and warnings
  - `paragraphs(raw: str, corrections: dict | None = None) -> tuple[list[str], list[str]]`
  - `unused_corrections(raw_texts: list[str], corrections: dict) -> list[str]`

Order of operations, per spec 3.3: decode entities → strip tags → apply corrections → collapse whitespace → warn on uncovered damage.

- [ ] **Step 1: Write the failing test**

```python
# cms/tests/test_bokun_text.py
import unittest
from cms import bokun_text

CORR = {'templ e grounds': 'temple grounds', 'wa l ked': 'walked'}


class TestClean(unittest.TestCase):
    def test_decodes_html_entities(self):
        text, _ = bokun_text.clean('Immerse yourself in &#34;Ichika Ichiei&#34;')
        self.assertEqual(text, 'Immerse yourself in "Ichika Ichiei"')

    def test_decodes_nbsp_as_a_plain_space(self):
        text, _ = bokun_text.clean('&nbsp;Meditation, gardens and matcha.')
        self.assertEqual(text, 'Meditation, gardens and matcha.')

    def test_strips_tags_and_collapses_whitespace(self):
        text, _ = bokun_text.clean('<p>Kamakura   has\n\nkept</p><p>its temples</p>')
        self.assertEqual(text, 'Kamakura has kept its temples')

    def test_applies_corrections(self):
        text, _ = bokun_text.clean('three templ e grounds wa l ked slowly', CORR)
        self.assertEqual(text, 'three temple grounds walked slowly')

    def test_corrections_apply_after_entity_decoding(self):
        text, _ = bokun_text.clean('&nbsp;templ e grounds', CORR)
        self.assertEqual(text, 'temple grounds')

    def test_warns_on_uncovered_damage(self):
        _, warnings = bokun_text.clean('a quiet passag e through', {})
        self.assertTrue(any('passag e through' in w for w in warnings))

    def test_no_warning_once_covered_by_corrections(self):
        _, warnings = bokun_text.clean('templ e grounds', CORR)
        self.assertEqual(warnings, [])

    def test_real_short_words_are_not_flagged_as_damage(self):
        for phrase in ['walk to Hase', 'one of three', 'tea is served',
                       'made by hand', 'sit in silence', 'up at dawn']:
            _, warnings = bokun_text.clean(phrase, {})
            self.assertEqual(warnings, [], f'false positive on {phrase!r}')

    def test_paragraphs_split_on_blank_lines(self):
        paras, _ = bokun_text.paragraphs('First para.\n\nSecond para.\n\n\nThird.')
        self.assertEqual(paras, ['First para.', 'Second para.', 'Third.'])

    def test_paragraphs_split_on_block_tags(self):
        paras, _ = bokun_text.paragraphs('<p>One.</p><p>Two.</p>')
        self.assertEqual(paras, ['One.', 'Two.'])

    def test_unused_corrections_reported(self):
        unused = bokun_text.unused_corrections(['temple grounds already fixed'], CORR)
        self.assertIn('templ e grounds', unused)
        self.assertIn('wa l ked', unused)

    def test_none_and_empty_are_safe(self):
        self.assertEqual(bokun_text.clean(None), ('', []))
        self.assertEqual(bokun_text.clean(''), ('', []))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest cms.tests.test_bokun_text -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cms.bokun_text'`

- [ ] **Step 3: Write minimal implementation**

```python
# cms/bokun_text.py
"""Normalise Bokun product copy.

Bokun text arrives with HTML entities, markup, and spacing damage consistent
with machine translation or a PDF paste. Corrections are a reviewed map rather
than an algorithm: the whole tier corpus holds only four damage sites, and no
word list exists on the build machine to validate a rejoin against. See spec
section 3.3.
"""
import html
import re

_BLOCK = re.compile(r'(?i)</(?:p|div|li|h[1-6])\s*>|<br\s*/?>')
_TAG = re.compile(r'<[^>]+>')
_WS = re.compile(r'[^\S\n]+')

# Genuine one- and two-letter English words, so the damage detector does not
# flag ordinary prose.
_SHORT_WORDS = {
    'a', 'i', 'am', 'an', 'as', 'at', 'be', 'by', 'do', 'go', 'he', 'hi', 'if',
    'in', 'is', 'it', 'me', 'my', 'no', 'of', 'oh', 'ok', 'on', 'or', 'so',
    'to', 'up', 'us', 'we',
}

# word, stray 1-2 letter token, word
_DAMAGE = re.compile(r'\b([A-Za-z]{2,})\s+([A-Za-z]{1,2})\s+([A-Za-z]{2,})\b')


def _decode(raw):
    text = html.unescape(raw or '')
    # html.unescape turns &nbsp; into U+00A0. Written as an escape on purpose:
    # a literal non-breaking space in source is invisible and unmaintainable.
    return text.replace('\u00a0', ' ')


def _apply_corrections(text, corrections):
    for bad, good in (corrections or {}).items():
        text = text.replace(bad, good)
    return text


def _warn(text):
    warnings = []
    for m in _DAMAGE.finditer(text):
        if m.group(2).lower() in _SHORT_WORDS:
            continue
        warnings.append(
            f'suspected spacing damage, not covered by corrections: {m.group(0)!r}')
    return warnings


def clean(raw, corrections=None):
    text = _decode(raw)
    text = _BLOCK.sub(' ', text)
    text = _TAG.sub(' ', text)
    text = _apply_corrections(text, corrections)
    text = _WS.sub(' ', text).replace('\n', ' ')
    text = re.sub(r' +', ' ', text).strip()
    return text, _warn(text)


def paragraphs(raw, corrections=None):
    text = _decode(raw)
    text = _BLOCK.sub('\n\n', text)
    text = _TAG.sub(' ', text)
    text = _apply_corrections(text, corrections)
    out, warnings = [], []
    for chunk in re.split(r'\n\s*\n+', text):
        chunk = re.sub(r'\s+', ' ', chunk).strip()
        if chunk:
            out.append(chunk)
            warnings.extend(_warn(chunk))
    return out, warnings


def unused_corrections(raw_texts, corrections):
    blob = ' '.join(_decode(t) for t in raw_texts)
    return [bad for bad in (corrections or {}) if bad not in blob]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest cms.tests.test_bokun_text -v`
Expected: 12 tests PASS

If `test_real_short_words_are_not_flagged_as_damage` fails on a phrase, add the offending token to `_SHORT_WORDS` — do not loosen the regex.

- [ ] **Step 5: Commit**

```bash
git add cms/bokun_text.py cms/tests/test_bokun_text.py
git commit -m "Add Bokun text normalisation with a reviewed correction map

Bokun copy carries HTML entities, markup and intra-word spacing damage. Repairs
come from a reviewed map in tours-config.json rather than an algorithm: the tier
corpus holds only four damage sites, there is no word list on the build machine
to validate a rejoin against, and validating against the client's own copy fails
because the damaged words appear zero times undamaged.

Uncovered damage sites warn instead of being guessed at, so new damage surfaces
when the client adds tours.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Price derivation

**Files:**
- Create: `cms/bokun_price.py`
- Test: `cms/tests/test_bokun_price.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `rows(availability: list, pricing_categories: list) -> list[dict]` — each `{'category': str|None, 'min': int|None, 'max': int|None, 'amount': int, 'currency': str}`
  - `from_price(price_rows: list[dict]) -> dict | None` — `{'amount': int, 'currency': str, 'category': str|None}`
  - `format_from(fp: dict | None, lang: str) -> str`
  - `format_full(price_rows: list[dict], lang: str) -> list[str]`

Rule (spec 3.5): the "from" price is the lowest **Adult**-category amount across all group tiers; if no Adult category exists, the lowest amount of any category, and the label drops "per adult".

Real data to hold in mind: Ikebana `1273232` has one ADULT category with tiers 1–2 → ¥44,000 and 3,4,5,6 → ¥21,000, so its from-price is ¥21,000. Candle-making `1273235` is ¥29,000 (1–2) / ¥12,000 (3,4) → ¥12,000. `1273194` and `1275339` return no prices at all → `None`.

- [ ] **Step 1: Write the failing test**

```python
# cms/tests/test_bokun_price.py
import unittest
from cms import bokun_price

CATS = [{'id': 1, 'title': 'Adult'}, {'id': 2, 'title': 'Child'}, {'id': 3, 'title': 'Infant'}]


def avail(units):
    return [{'pricesByRate': [{'activityRateId': 9, 'pricePerCategoryUnit': units}]}]


def unit(cat_id, amount, mn=None, mx=None):
    return {'id': cat_id, 'amount': {'amount': float(amount), 'currency': 'JPY'},
            'minParticipantsRequired': mn, 'maxParticipantsRequired': mx}


class TestRows(unittest.TestCase):
    def test_maps_category_ids_to_titles(self):
        r = bokun_price.rows(avail([unit(1, 12000, 1, 6), unit(2, 10000, 1, 6)]), CATS)
        self.assertEqual([(x['category'], x['amount']) for x in r],
                         [('Adult', 12000), ('Child', 10000)])

    def test_unknown_category_id_yields_none_category(self):
        r = bokun_price.rows(avail([unit(99, 5000)]), CATS)
        self.assertIsNone(r[0]['category'])

    def test_reads_only_the_first_slot_with_prices(self):
        a = [{'pricesByRate': []}] + avail([unit(1, 21000, 3, 3)])
        self.assertEqual(bokun_price.rows(a, CATS)[0]['amount'], 21000)

    def test_empty_availability_is_empty(self):
        self.assertEqual(bokun_price.rows([], CATS), [])


class TestFromPrice(unittest.TestCase):
    def test_ikebana_takes_the_lowest_adult_tier(self):
        r = bokun_price.rows(avail([unit(1, 44000, 1, 2), unit(1, 21000, 3, 3),
                                    unit(1, 21000, 4, 4)]), CATS)
        self.assertEqual(bokun_price.from_price(r),
                         {'amount': 21000, 'currency': 'JPY', 'category': 'Adult'})

    def test_ignores_cheaper_child_and_infant_rows(self):
        r = bokun_price.rows(avail([unit(1, 12000, 1, 6), unit(2, 10000, 1, 6),
                                    unit(3, 0, 1, 6)]), CATS)
        self.assertEqual(bokun_price.from_price(r)['amount'], 12000)

    def test_falls_back_to_lowest_of_any_category_when_no_adult(self):
        r = bokun_price.rows(avail([unit(2, 10000), unit(3, 4000)]), CATS)
        self.assertEqual(bokun_price.from_price(r),
                         {'amount': 4000, 'currency': 'JPY', 'category': 'Child'})

    def test_unpriced_product_is_none(self):
        self.assertIsNone(bokun_price.from_price([]))


class TestFormat(unittest.TestCase):
    def test_english_from_price_per_adult(self):
        fp = {'amount': 21000, 'currency': 'JPY', 'category': 'Adult'}
        self.assertEqual(bokun_price.format_from(fp, 'en'), 'from ¥21,000 per adult')

    def test_japanese_from_price_per_adult(self):
        fp = {'amount': 21000, 'currency': 'JPY', 'category': 'Adult'}
        self.assertEqual(bokun_price.format_from(fp, 'ja'), '¥21,000〜（大人おひとり）')

    def test_drops_per_adult_when_there_is_no_adult_category(self):
        fp = {'amount': 4000, 'currency': 'JPY', 'category': 'Child'}
        self.assertEqual(bokun_price.format_from(fp, 'en'), 'from ¥4,000')
        self.assertEqual(bokun_price.format_from(fp, 'ja'), '¥4,000〜')

    def test_unpriced_formats_empty(self):
        self.assertEqual(bokun_price.format_from(None, 'en'), '')

    def test_full_breakdown_lists_category_and_tier(self):
        r = bokun_price.rows(avail([unit(1, 44000, 1, 2), unit(1, 21000, 3, 6)]), CATS)
        self.assertEqual(bokun_price.format_full(r, 'en'),
                         ['Adult, 1–2 guests: ¥44,000', 'Adult, 3–6 guests: ¥21,000'])

    def test_full_breakdown_omits_tier_when_unbounded(self):
        r = bokun_price.rows(avail([unit(1, 23000)]), CATS)
        self.assertEqual(bokun_price.format_full(r, 'en'), ['Adult: ¥23,000'])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest cms.tests.test_bokun_price -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cms.bokun_price'`

- [ ] **Step 3: Write minimal implementation**

```python
# cms/bokun_price.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest cms.tests.test_bokun_price -v`
Expected: 14 tests PASS

- [ ] **Step 5: Commit**

```bash
git add cms/bokun_price.py cms/tests/test_bokun_price.py
git commit -m "Derive display prices from Bokun availability

Bokun prices vary by passenger category and by group-size tier at once, so no
tour has a single price. Cards show 'from X per adult' using the lowest adult
amount across tiers; detail pages get the full breakdown. Products with no
configured price resolve to None so they can fall to the in-preparation layout.

Child and infant rows are excluded from the 'from' figure so a tour cannot
advertise an infant price as its headline.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Signed API client

**Files:**
- Create: `cms/bokun_client.py`
- Test: `cms/tests/test_bokun_client.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `BokunError(Exception)`
  - `load_credentials(path: str | None = None) -> tuple[str, str]` — reads `~/.bokun-api.env`
  - `sign(secret: str, date: str, access_key: str, method: str, path: str) -> str`
  - `BokunClient(access_key, secret, transport=None)` with `.get(path)` and `.post(path, body)`

`transport` is a callable `(method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, bytes]`. Tests inject a fake; production uses `urllib`.

- [ ] **Step 1: Write the failing test**

```python
# cms/tests/test_bokun_client.py
import base64, hashlib, hmac, json, os, tempfile, unittest
from cms import bokun_client


class TestSign(unittest.TestCase):
    def test_signature_matches_the_documented_scheme(self):
        got = bokun_client.sign('sec', '2026-08-25 10:00:00', 'AK', 'GET', '/x.json/1')
        want = base64.b64encode(hmac.new(
            b'sec', b'2026-08-25 10:00:00AKGET/x.json/1', hashlib.sha1).digest()).decode()
        self.assertEqual(got, want)


class TestCredentials(unittest.TestCase):
    def test_reads_keys_and_ignores_comments_and_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'env')
            with open(p, 'w') as f:
                f.write('# comment\nBOKUN_ACCESS_KEY="ak"\nBOKUN_SECRET_KEY=sk\n\n')
            self.assertEqual(bokun_client.load_credentials(p), ('ak', 'sk'))

    def test_missing_key_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'env')
            with open(p, 'w') as f:
                f.write('BOKUN_ACCESS_KEY=ak\n')
            with self.assertRaises(bokun_client.BokunError):
                bokun_client.load_credentials(p)


class FakeTransport:
    def __init__(self, status=200, payload=b'{"ok":true}'):
        self.status, self.payload, self.calls = status, payload, []

    def __call__(self, method, url, headers, body):
        self.calls.append({'method': method, 'url': url, 'headers': headers, 'body': body})
        return self.status, self.payload


class TestClient(unittest.TestCase):
    def test_get_sends_the_three_auth_headers(self):
        t = FakeTransport()
        bokun_client.BokunClient('AK', 'sec', transport=t).get('/activity.json/1')
        h = t.calls[0]['headers']
        self.assertEqual(h['X-Bokun-AccessKey'], 'AK')
        self.assertIn('X-Bokun-Date', h)
        self.assertIn('X-Bokun-Signature', h)
        self.assertEqual(t.calls[0]['url'], 'https://api.bokun.io/activity.json/1')

    def test_signature_covers_the_path_including_query(self):
        t = FakeTransport()
        c = bokun_client.BokunClient('AK', 'sec', transport=t)
        c.get('/activity.json/1?lang=EN')
        date = t.calls[0]['headers']['X-Bokun-Date']
        self.assertEqual(t.calls[0]['headers']['X-Bokun-Signature'],
                         bokun_client.sign('sec', date, 'AK', 'GET', '/activity.json/1?lang=EN'))

    def test_post_sends_json_body_and_parses_response(self):
        t = FakeTransport(payload=b'{"totalHits":11}')
        c = bokun_client.BokunClient('AK', 'sec', transport=t)
        self.assertEqual(c.post('/activity.json/search', {'page': 1}), {'totalHits': 11})
        self.assertEqual(json.loads(t.calls[0]['body']), {'page': 1})
        self.assertEqual(t.calls[0]['method'], 'POST')

    def test_non_2xx_raises_with_the_path(self):
        c = bokun_client.BokunClient('AK', 'sec', transport=FakeTransport(status=404, payload=b'nope'))
        with self.assertRaises(bokun_client.BokunError) as ctx:
            c.get('/missing.json')
        self.assertIn('/missing.json', str(ctx.exception))

    def test_credentials_never_appear_in_the_error(self):
        c = bokun_client.BokunClient('AKSECRETVALUE', 'sec', transport=FakeTransport(status=500))
        with self.assertRaises(bokun_client.BokunError) as ctx:
            c.get('/x')
        self.assertNotIn('AKSECRETVALUE', str(ctx.exception))
        self.assertNotIn('sec', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest cms.tests.test_bokun_client -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cms.bokun_client'`

- [ ] **Step 3: Write minimal implementation**

```python
# cms/bokun_client.py
"""Bokun native REST client.

Auth is HMAC-SHA1 over date + access key + method + path. The transport is
injectable so the build's data layer can be tested without network access.
Credentials must never reach logs or error messages.
"""
import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = 'https://api.bokun.io'
DEFAULT_ENV = os.path.join(os.path.expanduser('~'), '.bokun-api.env')


class BokunError(Exception):
    pass


def load_credentials(path=None):
    path = path or DEFAULT_ENV
    values = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                values[k.strip()] = v.strip().strip('"').strip("'")
    except OSError as e:
        raise BokunError(f'cannot read Bokun credentials at {path}: {e.strerror}')
    try:
        return values['BOKUN_ACCESS_KEY'], values['BOKUN_SECRET_KEY']
    except KeyError as missing:
        raise BokunError(f'{path} is missing {missing}')


def sign(secret, date, access_key, method, path):
    msg = (date + access_key + method + path).encode()
    return base64.b64encode(hmac.new(secret.encode(), msg, hashlib.sha1).digest()).decode()


def _urllib_transport(method, url, headers, body):
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except OSError as e:
        raise BokunError(f'network error calling Bokun: {e}')


class BokunClient:
    def __init__(self, access_key, secret, transport=None):
        self._ak = access_key
        self._sk = secret
        self._transport = transport or _urllib_transport

    def _call(self, method, path, body=None):
        date = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        headers = {
            'X-Bokun-Date': date,
            'X-Bokun-AccessKey': self._ak,
            'X-Bokun-Signature': sign(self._sk, date, self._ak, method, path),
            'Accept': 'application/json',
            'Content-Type': 'application/json;charset=UTF-8',
        }
        payload = json.dumps(body).encode() if body is not None else None
        status, raw = self._transport(method, BASE + path, headers, payload)
        if not 200 <= status < 300:
            # Deliberately excludes headers: they carry the access key.
            raise BokunError(f'Bokun {method} {path} returned {status}')
        try:
            return json.loads(raw)
        except ValueError:
            raise BokunError(f'Bokun {method} {path} returned unparseable JSON')

    def get(self, path):
        return self._call('GET', path)

    def post(self, path, body):
        return self._call('POST', path, body)


def from_env(path=None, transport=None):
    ak, sk = load_credentials(path)
    return BokunClient(ak, sk, transport=transport)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest cms.tests.test_bokun_client -v`
Expected: 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add cms/bokun_client.py cms/tests/test_bokun_client.py
git commit -m "Add signed Bokun REST client with injectable transport

HMAC-SHA1 over date + access key + method + path, verified against the live API.
The transport is injected so the data layer is testable with no network, and
errors deliberately omit headers because those carry the access key.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Bokun source adapter

Emits records in the *same shape* as `cms/tours-fixture.json` entries, so `tour_model()` needs almost no change.

**Files:**
- Create: `cms/bokun_source.py`
- Create: `cms/tests/record_fixtures.py`
- Create: `cms/tests/data/` (recorded responses, committed)
- Test: `cms/tests/test_bokun_source.py`

**Interfaces:**
- Consumes: `cms.tours_config` (`load`, `catalogue_ids`, `tour_entry`, `corrections`), `cms.bokun_text` (`clean`, `paragraphs`, `unused_corrections`), `cms.bokun_price` (`rows`, `from_price`, `format_from`, `format_full`), `cms.bokun_client` (`BokunClient`).
- Produces:
  - `catalogue(client, cfg) -> list[int]` — product list first, then allowlist
  - `to_record(activity: dict, availability: list, entry: dict, corr: dict) -> tuple[dict, list[str]]`
  - `fetch_records(client, cfg) -> tuple[list[dict], list[str]]`

Record keys, matching the fixture plus four additions:

```
id, number, titleEn, titleJa, subEn, subJa, area, themes, length,
hoursEn, hoursJa, cover{url}, coverCaptionEn, coverCaptionJa,
priceEn, priceJa, ledeEn, ledeJa,
includedEn/Ja, notIncludedEn/Ja, notAllowedEn/Ja, notSuitableEn/Ja
+ bokunId, widgets, priceRows, jaReviewed
```

Mapping rules:
- `id` ← `entry['slug']`; `number` ← `entry['number']`
- `titleEn` ← cleaned `title`; `subEn` ← cleaned `excerpt`; `ledeEn` ← cleaned `description`
- Japanese fields: Bokun holds no Japanese, so `*Ja` mirrors `*En` **unless** `entry['jaReviewed']` is true, in which case the `?lang=ja` response is used. See spec section 4.
- `hoursEn` ← `durationText` from the EN response; `hoursJa` ← `durationText` from the JA response (this one field really does localise)
- `cover.url` ← `photos[0].originalUrl`; `coverCaption*` ← `photos[0].alternateText` or empty
- `area`/`length`/`themes` ← `entry`, falling back to `googlePlace.city` and a duration heuristic
- `included*` etc. ← newline-joined `agendaItems` titles is **wrong**; leave these empty. Bokun has no inclusions data, and the chips must not be invented. Task 7 hides empty chip groups.
- `priceEn`/`priceJa` ← `format_from(...)`; `priceRows` ← `rows(...)`

- [ ] **Step 1: Record real API responses as test fixtures**

```python
# cms/tests/record_fixtures.py
"""Record real Bokun responses into cms/tests/data/ so tests run offline.

Run manually when the fixtures need refreshing:
    python3 cms/tests/record_fixtures.py
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from cms import bokun_client, tours_config  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def main():
    os.makedirs(DATA, exist_ok=True)
    client = bokun_client.from_env()
    cfg = tours_config.load()
    today = datetime.now(timezone.utc).date()
    end = today + timedelta(days=75)
    for pid in tours_config.catalogue_ids(cfg):
        for lang in ('EN', 'ja'):
            d = client.get(f'/activity.json/{pid}?lang={lang}')
            _write(f'activity-{pid}-{lang}.json', d)
        av = client.get(f'/activity.json/{pid}/availabilities?start={today}&end={end}')
        _write(f'availability-{pid}.json', av)
    print('recorded fixtures for', tours_config.catalogue_ids(cfg))


def _write(name, data):
    with open(os.path.join(DATA, name), 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
```

Run: `python3 cms/tests/record_fixtures.py`
Expected: writes 12 files into `cms/tests/data/` (4 products × EN + ja + availability).

Then confirm no credentials leaked into the fixtures:

Run: `grep -rl -e "$(sed -n 's/^BOKUN_ACCESS_KEY=//p' ~/.bokun-api.env | tr -d '\"')" cms/tests/data/ || echo CLEAN`
Expected: `CLEAN`

- [ ] **Step 2: Write the failing test**

```python
# cms/tests/test_bokun_source.py
import json, os, unittest
from cms import bokun_source, tours_config

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
IKEBANA, CANDLE, ZEN, SWORD = 1273232, 1273235, 1273194, 1275339


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


class FakeClient:
    """Serves the recorded fixtures and records the paths asked for."""

    def __init__(self, product_list=None):
        self.paths, self._list = [], product_list

    def get(self, path):
        self.paths.append(path)
        if path.startswith('/product-list.json/list'):
            return self._list if self._list is not None else []
        if '/availabilities' in path:
            pid = int(path.split('/')[2])
            return load(f'availability-{pid}.json')
        if path.startswith('/activity.json/'):
            pid = int(path.split('/')[2].split('?')[0])
            lang = 'ja' if 'lang=ja' in path else 'EN'
            return load(f'activity-{pid}-{lang}.json')
        raise AssertionError('unexpected path ' + path)

    def post(self, path, body):
        raise AssertionError('no POST expected')


CFG = {
    'productListName': 'Website',
    'allowlist': [IKEBANA, CANDLE, ZEN, SWORD],
    'corrections': {'templ e grounds': 'temple grounds', 'wa l ked': 'walked',
                    'passag e through': 'passage through',
                    'templ e cuisine': 'temple cuisine'},
    'tours': {
        str(IKEBANA): {'slug': 'ikebana-ichigo-ichie', 'number': '01', 'area': 'Kamakura',
                       'length': 'Half-day', 'themes': ['Arts & Craft'], 'jaReviewed': False,
                       'widgets': {'en': 'CH/experience-calendar/1273232'}},
        str(CANDLE): {'slug': 'candle-making', 'number': '02', 'area': 'Kamakura',
                      'length': 'Half-day', 'themes': ['Arts & Craft'], 'jaReviewed': False,
                      'widgets': {}},
        str(ZEN): {'slug': 'zen-journey', 'number': '03', 'area': 'Kamakura',
                   'length': 'Half-day', 'themes': ['Walking'], 'jaReviewed': False,
                   'widgets': {}},
        str(SWORD): {'slug': 'swordsmithing', 'number': '04', 'area': 'Kamakura',
                     'length': 'Half-day', 'themes': ['Arts & Craft'], 'jaReviewed': False,
                     'widgets': {}},
    },
}


class TestCatalogue(unittest.TestCase):
    def test_prefers_the_named_product_list(self):
        c = FakeClient(product_list=[{'id': 77, 'title': 'Website',
                                      'items': [{'activityId': IKEBANA}]}])
        self.assertEqual(bokun_source.catalogue(c, CFG), [IKEBANA])

    def test_falls_back_to_the_allowlist_when_no_list_exists(self):
        self.assertEqual(bokun_source.catalogue(FakeClient(product_list=[]), CFG),
                         [IKEBANA, CANDLE, ZEN, SWORD])

    def test_ignores_product_lists_with_a_different_name(self):
        c = FakeClient(product_list=[{'id': 1, 'title': 'OTA', 'items': [{'activityId': 999}]}])
        self.assertEqual(bokun_source.catalogue(c, CFG), [IKEBANA, CANDLE, ZEN, SWORD])


class TestRecords(unittest.TestCase):
    def setUp(self):
        self.records, self.warnings = bokun_source.fetch_records(FakeClient(), CFG)
        self.by_slug = {r['id']: r for r in self.records}

    def test_one_record_per_catalogue_product(self):
        self.assertEqual(sorted(self.by_slug),
                         ['candle-making', 'ikebana-ichigo-ichie', 'swordsmithing', 'zen-journey'])

    def test_slug_and_number_come_from_config_not_bokun(self):
        r = self.by_slug['ikebana-ichigo-ichie']
        self.assertEqual(r['id'], 'ikebana-ichigo-ichie')
        self.assertEqual(r['number'], '01')
        self.assertEqual(r['bokunId'], IKEBANA)

    def test_title_is_cleaned_of_entities(self):
        for r in self.records:
            self.assertNotIn('&#', r['titleEn'])
            self.assertNotIn('&nbsp;', r['ledeEn'])

    def test_corrections_are_applied_to_the_lede(self):
        lede = self.by_slug['zen-journey']['ledeEn'] + ' ' + self.by_slug['zen-journey']['subEn']
        self.assertNotIn('templ e', lede)
        self.assertNotIn('wa l ked', lede)

    def test_ikebana_from_price_is_the_lowest_adult_tier(self):
        self.assertEqual(self.by_slug['ikebana-ichigo-ichie']['priceEn'],
                         'from ¥21,000 per adult')

    def test_candle_from_price_is_the_lowest_adult_tier(self):
        self.assertEqual(self.by_slug['candle-making']['priceEn'], 'from ¥12,000 per adult')

    def test_unpriced_products_have_no_price_and_no_price_rows(self):
        for slug in ('zen-journey', 'swordsmithing'):
            self.assertEqual(self.by_slug[slug]['priceEn'], '')
            self.assertEqual(self.by_slug[slug]['priceRows'], [])

    def test_japanese_mirrors_english_until_jaReviewed(self):
        r = self.by_slug['ikebana-ichigo-ichie']
        self.assertEqual(r['titleJa'], r['titleEn'])
        self.assertEqual(r['ledeJa'], r['ledeEn'])

    def test_duration_text_does_localise_even_when_unreviewed(self):
        r = self.by_slug['ikebana-ichigo-ichie']
        self.assertNotEqual(r['hoursJa'], r['hoursEn'])

    def test_cover_comes_from_the_first_photo(self):
        self.assertTrue(self.by_slug['ikebana-ichigo-ichie']['cover']['url'].startswith('http'))

    def test_inclusion_chips_are_empty_because_bokun_has_no_such_data(self):
        r = self.by_slug['ikebana-ichigo-ichie']
        for f in ('includedEn', 'notIncludedEn', 'notAllowedEn', 'notSuitableEn'):
            self.assertEqual(r[f], '')

    def test_widgets_carry_through_from_config(self):
        self.assertEqual(self.by_slug['ikebana-ichigo-ichie']['widgets'],
                         {'en': 'CH/experience-calendar/1273232'})

    def test_no_ota_product_can_appear(self):
        for r in self.records:
            self.assertNotIn(r['bokunId'],
                             [1272734, 1272756, 1272817, 1272825, 1272835, 1272849, 1273963])

    def test_uncovered_damage_surfaces_as_a_warning(self):
        records, warnings = bokun_source.fetch_records(
            FakeClient(), dict(CFG, corrections={}))
        self.assertTrue(any('spacing damage' in w for w in warnings))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m unittest cms.tests.test_bokun_source -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cms.bokun_source'`

- [ ] **Step 4: Write minimal implementation**

```python
# cms/bokun_source.py
"""Fetch the Zenrise-tier products from Bokun as fixture-shaped records.

Records use exactly the keys of cms/tours-fixture.json entries so that
build-tours.py's tour_model() and every downstream renderer stay unchanged.
Four keys are added: bokunId, widgets, priceRows, jaReviewed.
"""
from datetime import datetime, timedelta, timezone

from . import bokun_price, bokun_text, tours_config

PAIR_FIELDS = ('title', 'sub', 'lede', 'coverCaption',
               'included', 'notIncluded', 'notAllowed', 'notSuitable')


def catalogue(client, cfg):
    """Product list by name if it exists, otherwise the config allowlist."""
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
                    return ids
    return tours_config.catalogue_ids(cfg)


def _length_from_duration(duration_text):
    digits = ''.join(c for c in (duration_text or '') if c.isdigit() or c == ' ')
    first = digits.split()
    hours = int(first[0]) if first and first[0].isdigit() else 0
    return 'Full-day' if hours >= 5 else 'Half-day'


def to_record(activity, activity_ja, availability, entry, corr):
    warnings = []

    def cl(value):
        text, w = bokun_text.clean(value, corr)
        warnings.extend(w)
        return text

    title = cl(activity.get('title'))
    sub = cl(activity.get('excerpt'))
    lede = cl(activity.get('description'))
    reviewed = bool(entry.get('jaReviewed'))

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
    }

    en_values = {'title': title, 'sub': sub, 'lede': lede, 'coverCaption': cover_cap,
                 'included': '', 'notIncluded': '', 'notAllowed': '', 'notSuitable': ''}
    for field in PAIR_FIELDS:
        rec[field + 'En'] = en_values[field]
        if reviewed and field in ('title', 'sub', 'lede'):
            src = {'title': 'title', 'sub': 'excerpt', 'lede': 'description'}[field]
            rec[field + 'Ja'] = cl((activity_ja or {}).get(src)) or en_values[field]
        else:
            # Bokun holds no Japanese product copy. Mirroring English is the
            # honest fallback; raw machine translation must not reach the site.
            rec[field + 'Ja'] = en_values[field]
    return rec, warnings


def fetch_records(client, cfg):
    corr = tours_config.corrections(cfg)
    today = datetime.now(timezone.utc).date()
    end = today + timedelta(days=75)
    records, warnings, raw_texts = [], [], []
    for pid in catalogue(client, cfg):
        entry = tours_config.tour_entry(cfg, pid)
        activity = client.get(f'/activity.json/{pid}?lang=EN')
        activity_ja = client.get(f'/activity.json/{pid}?lang=ja')
        availability = client.get(
            f'/activity.json/{pid}/availabilities?start={today}&end={end}')
        raw_texts += [activity.get('title') or '', activity.get('excerpt') or '',
                      activity.get('description') or '']
        rec, w = to_record(activity, activity_ja, availability, entry, corr)
        records.append(rec)
        warnings += [f'[{rec["id"]}] {x}' for x in w]
    for stale in bokun_text.unused_corrections(raw_texts, corr):
        warnings.append(f'correction no longer matches any source text, safe to '
                        f'prune from tours-config.json: {stale!r}')
    return records, warnings
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest cms.tests.test_bokun_source -v`
Expected: 17 tests PASS

If `test_ikebana_from_price_is_the_lowest_adult_tier` fails, print `bokun_price.rows(...)` for that product and check the recorded availability actually contains `pricesByRate` — availability windows shift, so re-run `record_fixtures.py` if the recorded window has gone stale.

- [ ] **Step 6: Commit**

```bash
git add cms/bokun_source.py cms/tests/record_fixtures.py cms/tests/data cms/tests/test_bokun_source.py
git commit -m "Fetch Zenrise-tier products from Bokun as fixture-shaped records

The adapter emits exactly the keys of tours-fixture.json entries, so
tour_model() and every downstream renderer remain the stable seam and this is a
new source rather than a rewrite.

Catalogue resolution prefers a Bokun product list named in config and falls back
to the explicit allowlist, never to 'all products'. Japanese mirrors English
until a tour is marked jaReviewed, because Bokun holds no Japanese product copy
and raw machine translation must not reach a premium site; durationText is the
one field that genuinely localises. Inclusion chips stay empty because Bokun has
no such data and inventing it would be worse than omitting it.

Tests run offline against recorded responses.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

# Phase 2 — Generator and templates

### Task 6: Wire the Bokun source into build-tours.py

**Files:**
- Modify: `cms/build-tours.py:64-90` (`fetch_tours`), `cms/build-tours.py:253-256` (`main` head)
- Create: `cms/tours-cache.json` (generated, committed)
- Test: `cms/tests/test_build_tours_source.py`

**Interfaces:**
- Consumes: `bokun_source.fetch_records`, `bokun_client.from_env`, `tours_config.load`.
- Produces: `load_records(source: str, client=None, cfg=None) -> tuple[list[dict], dict, list[str]]` returning `(records, cfg, warnings)`.

`build-tours.py` has a hyphen in its name, so it cannot be imported as a module. Add a thin importable module `cms/tours_build_source.py` holding `load_records`, and have `build-tours.py` import it. Do not rename `build-tours.py` — `.github/workflows/` and `cms/tours-setup.md` reference it.

CLI: `--source bokun` (default), `--source cache`, `--source fixture`. `--live` stays as an alias for `--source bokun` so existing docs keep working.

- [ ] **Step 1: Write the failing test**

```python
# cms/tests/test_build_tours_source.py
import json, os, tempfile, unittest
from cms import tours_build_source as tbs


class TestCache(unittest.TestCase):
    def test_writes_then_reads_the_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'cache.json')
            tbs.write_cache(p, [{'id': 'ikebana-ichigo-ichie'}])
            self.assertEqual(tbs.read_cache(p), [{'id': 'ikebana-ichigo-ichie'}])

    def test_missing_cache_reads_as_none(self):
        self.assertIsNone(tbs.read_cache('/nonexistent/cache.json'))

    def test_bokun_failure_falls_back_to_cache_with_a_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'cache.json')
            tbs.write_cache(p, [{'id': 'cached'}])

            def boom(client, cfg):
                raise RuntimeError('bokun down')

            recs, warnings = tbs.records_with_fallback(
                fetch=boom, client=None, cfg={}, cache_path=p)
            self.assertEqual(recs, [{'id': 'cached'}])
            self.assertTrue(any('cache' in w for w in warnings))

    def test_bokun_failure_with_no_cache_raises(self):
        def boom(client, cfg):
            raise RuntimeError('bokun down')

        with self.assertRaises(RuntimeError):
            tbs.records_with_fallback(fetch=boom, client=None, cfg={},
                                     cache_path='/nonexistent/c.json')

    def test_success_refreshes_the_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'cache.json')

            def ok(client, cfg):
                return [{'id': 'fresh'}], []

            recs, _ = tbs.records_with_fallback(fetch=ok, client=None, cfg={}, cache_path=p)
            self.assertEqual(recs, [{'id': 'fresh'}])
            self.assertEqual(tbs.read_cache(p), [{'id': 'fresh'}])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest cms.tests.test_build_tours_source -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cms.tours_build_source'`

- [ ] **Step 3: Write minimal implementation**

```python
# cms/tours_build_source.py
"""Source selection and cache for the tours build.

Lives apart from build-tours.py because that filename has a hyphen and cannot
be imported by tests.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(HERE, 'tours-cache.json')


def read_cache(path=None):
    try:
        with open(path or CACHE_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_cache(path, records):
    with open(path or CACHE_PATH, 'w') as f:
        json.dump(records, f, ensure_ascii=False, indent=1)


def records_with_fallback(fetch, client, cfg, cache_path=None):
    """Fetch from Bokun; on failure fall back to the committed cache.

    An API outage must never empty the tours pages.
    """
    try:
        records, warnings = fetch(client, cfg)
    except Exception as e:
        cached = read_cache(cache_path)
        if cached is None:
            raise
        return cached, [f'Bokun fetch failed ({e}); built from cache '
                        f'{cache_path or CACHE_PATH}. Prices may be stale.']
    write_cache(cache_path, records)
    return records, warnings


def load_records(source='bokun', cache_path=None):
    from . import bokun_client, bokun_source, tours_config
    cfg = tours_config.load()
    if source == 'cache':
        cached = read_cache(cache_path)
        if cached is None:
            raise RuntimeError('no tours cache to build from')
        return cached, cfg, ['built from cache by request']
    client = bokun_client.from_env()
    records, warnings = records_with_fallback(
        bokun_source.fetch_records, client, cfg, cache_path)
    return records, cfg, warnings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest cms.tests.test_build_tours_source -v`
Expected: 5 tests PASS

- [ ] **Step 5: Point build-tours.py at the new source**

Replace `fetch_tours` (currently `cms/build-tours.py:64-90`) with:

```python
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
```

And in `main()` replace the first two lines:

```python
def main():
    source = 'cache' if '--source' in sys.argv and 'cache' in sys.argv else 'bokun'
    contents, cfg = fetch_tours(source)
```

with an explicit parse:

```python
def main():
    source = 'bokun'
    if '--source' in sys.argv:
        source = sys.argv[sys.argv.index('--source') + 1]
    elif '--live' in sys.argv:
        source = 'bokun'          # retained alias, referenced by cms/tours-setup.md
    contents, cfg = fetch_tours(source)
```

`routes` is no longer available from a fixture; Bokun's `agendaItems` replace it. Change:

```python
    routes = json.load(open(os.path.join(HERE, 'tour-routes.json')))
    models = [tour_model(a, routes) for a in contents]
```

to:

```python
    models = [tour_model(a) for a in contents]
```

Task 7 updates `tour_model`'s signature to match.

- [ ] **Step 6: Verify the build runs end to end against live Bokun**

Run: `cd ~/projects/zenrise-staging && python3 cms/build-tours.py --source bokun`
Expected: prints any warnings, then `wrote 4 tour page(s)`. It is fine for this step to fail inside `tour_model` — Task 7 fixes that. What must succeed is fetching and the cache write:

Run: `python3 -c "import json;print(len(json.load(open('cms/tours-cache.json'))))"`
Expected: `4`

- [ ] **Step 7: Commit**

```bash
git add cms/tours_build_source.py cms/tests/test_build_tours_source.py cms/build-tours.py cms/tours-cache.json
git commit -m "Build tours from Bokun, with a committed cache as the outage floor

Source selection moves into an importable module because build-tours.py has a
hyphen in its name and cannot be imported by tests. --live is kept as an alias
for --source bokun so cms/tours-setup.md stays accurate.

A successful fetch refreshes cms/tours-cache.json; a failed fetch builds from it
and warns, so a Bokun outage can never empty the tours pages. With no cache at
all the build fails loudly rather than publishing nothing.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Price, prep-layout and chip plumbing

**Files:**
- Modify: `cms/build-tours.py` — `PRICE`/`THEME_SLUG` constants (lines 22-31), `tour_model` (91-107), `base_dict` (109-127), `common_slots` (134-151), `chips` (152-161), `route_rows` (162-179), `render_detail` (180-198), `card` (200-215), `tile` (216-231)
- Test: `cms/tests/test_tours_render.py`

**Interfaces:**
- Consumes: records from Task 5.
- Produces: `tour_model(a: dict) -> dict` — same `m` keys as before plus `m['bokun_id']`, `m['widgets']`, `m['price_rows']`; `m['full']` now means "has a price".

Changes:
1. Delete the `PRICE` dict — prices come from the record, never from a length lookup.
2. `m['full'] = bool(a.get('priceEn'))` — unpriced products get the prep layout (spec 3.5).
3. `m['price_key'] = None` always, and `m['price_en'] / m['price_ja']` come straight from the record, so the price renders as literal text with a per-tour i18n key.
4. `THEME_SLUG` gains `'Arts & Craft': 'arts'`. Unknown themes raise a clear error rather than `KeyError`.
5. `chips()` returns `''` for an empty field, and `render_detail` omits the whole chip section when every group is empty.
6. `route_rows()` reads `m['route']` built from `agendaItems`.

- [ ] **Step 1: Write the failing test**

```python
# cms/tests/test_tours_render.py
import importlib.util, os, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_tours', os.path.join(ROOT, 'cms', 'build-tours.py'))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)


def record(**over):
    r = {'id': 'ikebana-ichigo-ichie', 'bokunId': 1273232, 'number': '01',
         'area': 'Kamakura', 'length': 'Half-day', 'themes': ['Arts & Craft'],
         'cover': {'url': 'https://img/x.jpg'},
         'hoursEn': '1 hour and 30 minutes', 'hoursJa': '1 時間30 分',
         'priceEn': 'from ¥21,000 per adult', 'priceJa': '¥21,000〜（大人おひとり）',
         'priceRows': [{'category': 'Adult', 'min': 3, 'max': 6,
                        'amount': 21000, 'currency': 'JPY'}],
         'widgets': {'en': 'CH/experience-calendar/1273232'}, 'jaReviewed': False,
         'titleEn': 'Ikebana', 'titleJa': 'Ikebana',
         'subEn': 'A private workshop.', 'subJa': 'A private workshop.',
         'ledeEn': 'Ninety minutes with a master.', 'ledeJa': 'Ninety minutes with a master.',
         'coverCaptionEn': '', 'coverCaptionJa': '',
         'includedEn': '', 'includedJa': '', 'notIncludedEn': '', 'notIncludedJa': '',
         'notAllowedEn': '', 'notAllowedJa': '', 'notSuitableEn': '', 'notSuitableJa': '',
         'route': []}
    r.update(over)
    return r


class TestModel(unittest.TestCase):
    def test_priced_product_is_full(self):
        self.assertTrue(bt.tour_model(record())['full'])

    def test_unpriced_product_is_not_full(self):
        self.assertFalse(bt.tour_model(record(priceEn='', priceJa=''))['full'])

    def test_price_text_comes_from_the_record(self):
        m = bt.tour_model(record())
        self.assertEqual(m['price_en'], 'from ¥21,000 per adult')
        self.assertEqual(m['price_ja'], '¥21,000〜（大人おひとり）')

    def test_price_uses_a_per_tour_key_not_a_shared_length_key(self):
        self.assertIsNone(bt.tour_model(record())['price_key'])

    def test_bokun_id_and_widgets_carry_into_the_model(self):
        m = bt.tour_model(record())
        self.assertEqual(m['bokun_id'], 1273232)
        self.assertEqual(m['widgets'], {'en': 'CH/experience-calendar/1273232'})


class TestThemes(unittest.TestCase):
    def test_arts_and_craft_maps_to_a_slug(self):
        self.assertIn('arts', bt.card(bt.tour_model(record())))

    def test_unknown_theme_raises_a_readable_error(self):
        with self.assertRaises(bt.BuildError):
            bt.card(bt.tour_model(record(themes=['Nonexistent Theme'])))


class TestChips(unittest.TestCase):
    def test_empty_chip_field_renders_nothing(self):
        m = bt.tour_model(record())
        self.assertEqual(bt.chips(m, 'included', 'inc', {}, {}), '')

    def test_populated_chip_field_renders_items(self):
        m = bt.tour_model(record(includedEn='Guide\nEntrance fees',
                                 includedJa='Guide\nEntrance fees'))
        html = bt.chips(m, 'included', 'inc', {}, {})
        self.assertIn('Guide', html)
        self.assertIn('Entrance fees', html)


class TestCardAndTile(unittest.TestCase):
    def test_card_links_to_the_slug(self):
        self.assertIn('href="tour-ikebana-ichigo-ichie.html"', bt.card(bt.tour_model(record())))

    def test_card_shows_the_from_price(self):
        self.assertIn('from ¥21,000 per adult', bt.card(bt.tour_model(record())))

    def test_card_for_unpriced_tour_shows_no_price_text(self):
        html = bt.card(bt.tour_model(record(priceEn='', priceJa='')))
        self.assertNotIn('¥', html)

    def test_tile_links_to_the_slug(self):
        self.assertIn('href="tour-ikebana-ichigo-ichie.html"', bt.tile(bt.tour_model(record())))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest cms.tests.test_tours_render -v`
Expected: FAIL — `AttributeError: module 'build_tours' has no attribute 'BuildError'`, plus `tour_model()` signature errors.

- [ ] **Step 3: Write the implementation**

In `cms/build-tours.py`, delete the `PRICE` dict (lines 22-25) and add near the top:

```python
class BuildError(Exception):
    pass
```

Extend `THEME_SLUG` with `'Arts & Craft': 'arts',` and add a lookup helper:

```python
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
```

In `card()` and `tile()`, replace both uses of `AREA_KEY[m['area']]` with `area_key(m['area'])`. Without this a new area from Bokun or config raises a bare `KeyError` deep in an f-string.

Replace `tour_model` with:

```python
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
```

In `card()` and `tile()`, replace `' '.join(THEME_SLUG[t] for t in m['themes'])` with `' '.join(theme_slugs(m['themes']))`, and make the price span conditional in `card()`:

```python
    price_html = ('' if not m['price_en'] else
                  f'<span class="price" data-i18n="{K}_price">{esc(m["price_en"])}</span>')
```

then use `{price_html}` in the `t-foot` div in place of the old price span.

In `chips()`, return early:

```python
def chips(m, field, prefix, en, ja):
    if not m[field][0]:
        return ''
```

In `base_dict()`, add the per-tour price keys:

```python
    en[K + '_price'] = m['price_en']
    ja[K + '_price'] = m['price_ja']
```

In `render_detail()`, replace the `CAL_PRICE` line with the from-price and pass the full breakdown:

```python
        slots['CAL_PRICE'] = m['price_en']
        slots['PRICE_ROWS'] = '\n'.join(
            f'          <li>{esc(r)}</li>' for r in _price_lines(m))
```

and add:

```python
def _price_lines(m):
    sys.path.insert(0, os.path.dirname(HERE))
    from cms import bokun_price
    return bokun_price.format_full(m['price_rows'], 'en')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest cms.tests.test_tours_render -v`
Expected: 13 tests PASS

- [ ] **Step 5: Run the whole suite and the real build**

Run: `python3 -m unittest discover -s cms/tests -t . -v`
Expected: all tests PASS

Run: `python3 cms/build-tours.py --source cache`
Expected: `wrote 4 tour page(s): tour-ikebana-ichigo-ichie.html, tour-candle-making.html, tour-zen-journey.html (prep), tour-swordsmithing.html (prep)`

- [ ] **Step 6: Commit**

```bash
git add cms/build-tours.py cms/tests/test_tours_render.py
git commit -m "Render Bokun prices and route the unpriced to the prep layout

Prices are per tour and come from Bokun, so the shared Half-day/Full-day PRICE
lookup is deleted and each tour gets its own i18n key. 'full' now means 'has a
price' rather than 'has a lede', which sends The Zen Journey and Swordsmithing to
the in-preparation layout built on 8/11 — exactly what it was designed for.

Empty chip groups render nothing, because Bokun has no inclusions data and
inventing chips would be worse than omitting them. Unknown themes raise a
readable BuildError instead of a bare KeyError.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Replace the custom calendar with the Bokun widget

**Files:**
- Modify: `cms/templates/tour-detail.html` — replace lines 287-313 (`<aside class="cal" id="book">` … `</aside>`) and delete the calendar script block at lines 393-505
- Modify: `cms/build-tours.py` — `common_slots` / `render_detail` to fill `WIDGET_BLOCK`
- Test: `cms/tests/test_widget_embed.py`

**Interfaces:**
- Consumes: `m['widgets']`, `m['bokun_id']`, `m['full']`.
- Produces: `widget_block(m) -> str`.

The widget is a cross-origin iframe (spec 3.6), so styling happens in Bokun's panel, not here. Our markup only provides the mount point, the loader, and a `<noscript>` fallback to `/go/<slug>`.

Language: the widget path is per language and language is baked into the widget. Emit the EN widget as the mount, and record the JA path in a `data-widget-ja` attribute so a later language-switch hook can swap `data-src` without a template change.

- [ ] **Step 1: Write the failing test**

```python
# cms/tests/test_widget_embed.py
import importlib.util, os, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_tours', os.path.join(ROOT, 'cms', 'build-tours.py'))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)

CH = 'e2350ad8-80af-4c18-a21a-acae6d72283f'


def model(widgets, full=True, slug='ikebana-ichigo-ichie'):
    return {'id': slug, 'widgets': widgets, 'full': full, 'bokun_id': 1273232,
            'K': 'tours_' + slug}


class TestWidgetBlock(unittest.TestCase):
    def test_emits_loader_and_mount_for_the_en_widget(self):
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232'}))
        self.assertIn('BokunWidgetsLoader.js?bookingChannelUUID=' + CH, html)
        self.assertIn('class="bokunWidget"', html)
        self.assertIn(f'https://widgets.bokun.io/online-sales/{CH}/experience-calendar/1273232',
                      html)

    def test_records_the_ja_widget_for_later_language_switching(self):
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232',
                                      'ja': f'{CH}/experience-calendar/999'}))
        self.assertIn('data-widget-ja="https://widgets.bokun.io/online-sales/'
                      f'{CH}/experience-calendar/999"', html)

    def test_ja_falls_back_to_en_when_absent(self):
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232'}))
        self.assertNotIn('data-widget-ja', html)

    def test_noscript_points_at_the_go_redirect(self):
        html = bt.widget_block(model({'en': f'{CH}/experience-calendar/1273232'}))
        self.assertIn('<noscript>', html)
        self.assertIn('go/ikebana-ichigo-ichie', html)

    def test_no_widget_configured_yields_a_visible_placeholder_not_silence(self):
        html = bt.widget_block(model({}))
        self.assertIn('data-widget-missing', html)
        self.assertNotIn('bokunWidget', html)

    def test_unpriced_tour_gets_no_widget(self):
        self.assertEqual(bt.widget_block(model({'en': 'x/y/1'}, full=False)), '')


class TestTemplate(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, 'cms', 'templates', 'tour-detail.html')) as f:
            self.tpl = f.read()

    def test_template_has_a_widget_slot(self):
        self.assertIn('{{WIDGET_BLOCK}}', self.tpl)

    def test_custom_calendar_markup_is_gone(self):
        self.assertNotIn('aside class="cal"', self.tpl)
        self.assertNotIn('id="cal-days"', self.tpl)

    def test_custom_calendar_script_is_gone(self):
        self.assertNotIn('cal-go', self.tpl)
        self.assertNotIn('zenrise-booking-v1', self.tpl)

    def test_no_stale_template_slots_remain(self):
        for slot in ('{{CAL_PRICE}}',):
            self.assertNotIn(slot, self.tpl, f'{slot} left behind after calendar removal')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest cms.tests.test_widget_embed -v`
Expected: FAIL — `module 'build_tours' has no attribute 'widget_block'`

- [ ] **Step 3: Add `widget_block` to build-tours.py**

```python
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
        return (f'        <aside class="cal-missing" data-widget-missing="{m["id"]}">\n'
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
```

In `render_detail`, inside the `if m['full']:` branch, replace the `CAL_PRICE` assignment with:

```python
        slots['WIDGET_BLOCK'] = widget_block(m)
```

and add `slots['WIDGET_BLOCK'] = ''` to `common_slots()` so the prep template never sees an unfilled slot.

- [ ] **Step 4: Edit the template**

In `cms/templates/tour-detail.html`:

1. Replace lines 287-313 — the whole `<aside class="cal" id="book">` … `</aside>` block — with the single line:

```html
{{WIDGET_BLOCK}}
```

2. Delete the script block at lines 393-505 in its entirety (the vanilla calendar, its interim Tue/Thu/Sat availability rule, and the `zenrise-booking-v1` handoff). Keep the script block at 366-392.

3. Confirm no `{{CAL_PRICE}}` reference survives:

Run: `grep -n 'CAL_PRICE\|cal-go\|zenrise-booking-v1\|cal-days' cms/templates/tour-detail.html || echo CLEAN`
Expected: `CLEAN`

- [ ] **Step 5: Run tests and rebuild**

Run: `python3 -m unittest cms.tests.test_widget_embed -v`
Expected: 10 tests PASS

Run: `python3 cms/build-tours.py --source cache && grep -c bokunWidget tour-ikebana-ichigo-ichie.html`
Expected: `1`

- [ ] **Step 6: Verify the embed renders, headlessly**

```bash
cd ~/projects/zenrise-staging && python3 -m http.server 8031 --bind 127.0.0.1 &
SCRATCH=$(mktemp -d)
python3 -m venv $SCRATCH/v && $SCRATCH/v/bin/pip -q install playwright
$SCRATCH/v/bin/playwright install chromium
cat > $SCRATCH/check.py <<'PY'
from playwright.sync_api import sync_playwright
URL = "http://127.0.0.1:8031/tour-ikebana-ichigo-ichie.html"
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_context(viewport={"width":1600,"height":1200}).new_page()
    errs = []
    pg.on("console", lambda m: m.type == "error" and errs.append(m.text[:140]))
    pg.on("pageerror", lambda e: errs.append(str(e)[:140]))
    pg.goto(URL, wait_until="load"); pg.wait_for_timeout(9000)
    print("widget iframes:", pg.evaluate("document.querySelectorAll('.bokunWidget iframe').length"))
    print("iframe src    :", pg.evaluate("(document.querySelector('.bokunWidget iframe')||{}).src"))
    print("console errors:", errs[:3])
    pg.screenshot(path="/tmp/tour-widget.png", full_page=True)
    b.close()
PY
$SCRATCH/v/bin/python $SCRATCH/check.py
```

Expected: `widget iframes: 1`, an iframe src on `widgets.bokun.io`, and no console errors. Open `/tmp/tour-widget.png` and confirm the calendar sits in the page where the old one did.

- [ ] **Step 7: Commit**

```bash
git add cms/templates/tour-detail.html cms/build-tours.py cms/tests/test_widget_embed.py
git commit -m "Embed the Bokun calendar widget, retire the custom calendar

Deletes the vanilla calendar markup, its interim Tue/Thu/Sat availability rule
and the zenrise-booking-v1 handoff from the tour detail template; the widget owns
availability now. The design is preserved in archive/custom-booking/ and at tag
custom-booking-v1.

The widget is a cross-origin iframe, so it cannot inherit our CSS or the
domain-scoped Adobe kit — colour is configured in Bokun's panel and type will not
match. Because widget language is baked in rather than passed as a parameter, the
JA widget path rides along in data-widget-ja so a language-switch hook can swap
data-src later without touching the template.

A tour with no configured widget renders a visible placeholder rather than
silently omitting the booking control.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: JSON-LD, per-tour meta and sitemap

**Files:**
- Modify: `cms/build-tours.py` — add `json_ld(m)`, fill `META_DESC` and a new `{{JSON_LD}}` slot
- Modify: `cms/templates/tour-detail.html`, `cms/templates/tour-prep.html` — add `{{JSON_LD}}` before `</head>`
- Modify: `cms/build-news.py:350-374` (`render_sitemap`) — include tours
- Create: `cms/tours-index.json` (generated, committed)
- Test: `cms/tests/test_tours_seo.py`

**Interfaces:**
- Consumes: `m` from Task 7.
- Produces: `json_ld(m) -> str`, `meta_desc(m) -> str`, `write_tours_index(models) -> None`.

`build-news.py` is the sole writer of `sitemap.xml`, so tours reach it through `cms/tours-index.json` rather than a second writer.

- [ ] **Step 1: Write the failing test**

```python
# cms/tests/test_tours_seo.py
import importlib.util, json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_tours', os.path.join(ROOT, 'cms', 'build-tours.py'))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)


def model(**over):
    m = {'id': 'ikebana-ichigo-ichie', 'K': 'tours_ikebana-ichigo-ichie', 'num': '01',
         'area': 'Kamakura', 'length': 'Half-day', 'themes': ['Arts & Craft'],
         'cover': 'https://img/x.jpg', 'full': True, 'bokun_id': 1273232, 'widgets': {},
         'title': ('Ikebana', 'Ikebana'), 'sub': ('A private workshop.', ''),
         'lede': ('Ninety minutes with a master of the Sogetsu school.', ''),
         'hours': ('1 hour and 30 minutes', ''), 'coverCaption': ('', ''),
         'price_en': 'from ¥21,000 per adult', 'price_ja': '',
         'price_rows': [{'category': 'Adult', 'min': 3, 'max': 6,
                         'amount': 21000, 'currency': 'JPY'}],
         'route': []}
    m.update(over)
    return m


class TestJsonLd(unittest.TestCase):
    def test_emits_valid_json(self):
        raw = bt.json_ld(model())
        body = re.search(r'>(.*)</script>', raw, re.S).group(1)
        json.loads(body)

    def test_declares_a_product_with_an_offer(self):
        d = json.loads(re.search(r'>(.*)</script>', bt.json_ld(model()), re.S).group(1))
        self.assertEqual(d['@type'], 'Product')
        self.assertEqual(d['offers']['priceCurrency'], 'JPY')
        self.assertEqual(d['offers']['price'], 21000)

    def test_unpriced_tour_emits_no_offer(self):
        d = json.loads(re.search(r'>(.*)</script>',
                                 bt.json_ld(model(full=False, price_rows=[])), re.S).group(1))
        self.assertNotIn('offers', d)

    def test_escapes_a_closing_script_tag_in_copy(self):
        raw = bt.json_ld(model(title=('</script><script>alert(1)</script>', '')))
        self.assertNotIn('</script><script>', raw)


class TestMetaDesc(unittest.TestCase):
    def test_prefers_the_sub(self):
        self.assertEqual(bt.meta_desc(model()), 'A private workshop.')

    def test_falls_back_to_the_lede_truncated_on_a_word_boundary(self):
        d = bt.meta_desc(model(sub=('', ''), lede=('word ' * 60, '')))
        self.assertLessEqual(len(d), 160)
        self.assertFalse(d.endswith('wor'))

    def test_never_empty(self):
        self.assertTrue(bt.meta_desc(model(sub=('', ''), lede=('', ''))))


class TestTemplatesAndSitemap(unittest.TestCase):
    def test_both_templates_carry_the_json_ld_slot(self):
        for name in ('tour-detail.html', 'tour-prep.html'):
            with open(os.path.join(ROOT, 'cms', 'templates', name)) as f:
                self.assertIn('{{JSON_LD}}', f.read(), name)

    def test_sitemap_includes_tours_when_the_index_exists(self):
        news_spec = importlib.util.spec_from_file_location(
            'build_news', os.path.join(ROOT, 'cms', 'build-news.py'))
        bn = importlib.util.module_from_spec(news_spec)
        news_spec.loader.exec_module(bn)
        xml = bn.render_sitemap([])
        self.assertIn('https://zenrise.jp/tours.html', xml)
        self.assertIn('https://zenrise.jp/tour-ikebana-ichigo-ichie.html', xml)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest cms.tests.test_tours_seo -v`
Expected: FAIL — `module 'build_tours' has no attribute 'json_ld'`

- [ ] **Step 3: Implement in build-tours.py**

```python
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
```

Add to `common_slots(m)`:

```python
    slots['JSON_LD'] = json_ld(m)
    slots['META_DESC'] = esc(meta_desc(m))
```

(If `common_slots` already sets `META_DESC`, replace that line rather than adding a second.)

Call `write_tours_index(models)` in `main()` immediately after the detail-page loop.

- [ ] **Step 4: Add the slot to both templates**

In `cms/templates/tour-detail.html` and `cms/templates/tour-prep.html`, insert on the line directly before `</head>`:

```html
{{JSON_LD}}
```

- [ ] **Step 5: Teach build-news.py's sitemap about tours**

In `cms/build-news.py`, inside `render_sitemap`, after the existing static URLs are appended, add:

```python
    tours_index = os.path.join(HERE, 'tours-index.json')
    if os.path.exists(tours_index):
        with open(tours_index) as f:
            slugs = json.load(f)
        rows.append(f'  <url><loc>{SITE}/tours.html</loc></url>')
        for slug in slugs:
            rows.append(f'  <url><loc>{SITE}/tour-{slug}.html</loc></url>')
```

Use whatever the local list variable is actually called at `cms/build-news.py:352` in place of `rows`, and match the existing indentation and `SITE` constant.

- [ ] **Step 6: Run tests and both builds**

Run: `python3 -m unittest discover -s cms/tests -t . -v`
Expected: all PASS

Run: `python3 cms/build-tours.py --source cache && python3 cms/build-news.py && grep -c "tour-" sitemap.xml`
Expected: `4`

Validate the JSON-LD parses from the generated page:

Run: `python3 -c "
import re,json
h=open('tour-ikebana-ichigo-ichie.html').read()
d=json.loads(re.search(r'application/ld\+json\">(.*?)</script>',h,re.S).group(1).replace('<\\\\/','</'))
print(d['@type'], d['offers']['price'], d['offers']['priceCurrency'])"`
Expected: `Product 21000 JPY`

- [ ] **Step 7: Commit**

```bash
git add cms/build-tours.py cms/build-news.py cms/templates/tour-detail.html cms/templates/tour-prep.html cms/tours-index.json cms/tests/test_tours_seo.py sitemap.xml
git commit -m "Add tour Product JSON-LD, per-tour meta and sitemap entries

Prices bake into our own HTML so they are visible to search engines, which the
Bokun widget cannot provide: its pages are noindex,indexifembedded. Unpriced
tours emit no offer rather than a zero price.

Tours reach sitemap.xml through cms/tours-index.json because build-news.py is
the single writer of that file; tours.html itself was missing from the sitemap
and is now included.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

# Phase 3 — Automation and retirement

Nothing is deleted until its replacement is proven.

### Task 10: Scheduled rebuild

**Files:**
- Modify: `.github/workflows/` — the existing news webhook workflow (find with `ls .github/workflows/`)
- Create: `.github/workflows/rebuild-tours.yml`

**Interfaces:**
- Consumes: `cms/build-tours.py --source bokun`.
- Produces: a daily build plus manual dispatch.

Bokun cannot call a webhook at us (spec 3.7), so this is a schedule. Credentials come from repository secrets, written to `~/.bokun-api.env` at run time so `bokun_client.load_credentials` finds them unchanged.

- [ ] **Step 1: Inspect the existing workflow so the new one matches its conventions**

Run: `ls .github/workflows/ && cat .github/workflows/*.yml | head -60`
Expected: the news rebuild workflow; note its checkout action version, commit identity and push style.

- [ ] **Step 2: Write the workflow**

```yaml
# .github/workflows/rebuild-tours.yml
name: Rebuild tours from Bokun

on:
  schedule:
    - cron: '17 19 * * *'   # 04:17 JST daily, outside business hours
  workflow_dispatch:

jobs:
  rebuild:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4

      - name: Provide Bokun credentials
        env:
          BOKUN_ACCESS_KEY: ${{ secrets.BOKUN_ACCESS_KEY }}
          BOKUN_SECRET_KEY: ${{ secrets.BOKUN_SECRET_KEY }}
        run: |
          umask 077
          printf 'BOKUN_ACCESS_KEY=%s\nBOKUN_SECRET_KEY=%s\n' \
            "$BOKUN_ACCESS_KEY" "$BOKUN_SECRET_KEY" > "$HOME/.bokun-api.env"

      - name: Run the unit tests
        run: python3 -m unittest discover -s cms/tests -t . -v

      - name: Rebuild tours
        run: python3 cms/build-tours.py --source bokun

      - name: Rebuild the sitemap
        run: python3 cms/build-news.py || true

      - name: Commit any changes
        run: |
          git config user.name  'github-actions[bot]'
          git config user.email 'github-actions[bot]@users.noreply.github.com'
          if [ -n "$(git status --porcelain)" ]; then
            git add -A
            git commit -m 'Tours: scheduled rebuild from Bokun'
            git push
          else
            echo 'no changes'
          fi

      - name: Remove credentials
        if: always()
        run: rm -f "$HOME/.bokun-api.env"
```

- [ ] **Step 3: Add the repository secrets**

These cannot be set from the repo. Run:

```bash
gh secret set BOKUN_ACCESS_KEY --repo PerpetuaDev/zenrise-staging < <(sed -n 's/^BOKUN_ACCESS_KEY=//p' ~/.bokun-api.env | tr -d '"')
gh secret set BOKUN_SECRET_KEY --repo PerpetuaDev/zenrise-staging < <(sed -n 's/^BOKUN_SECRET_KEY=//p' ~/.bokun-api.env | tr -d '"')
gh secret list --repo PerpetuaDev/zenrise-staging
```

Expected: both secrets listed.

- [ ] **Step 4: Trigger it once and confirm**

```bash
git add .github/workflows/rebuild-tours.yml
git commit -m "Add scheduled Bokun tours rebuild

Bokun cannot call a webhook at us, so prices and copy refresh on a daily
schedule; availability is never baked, so a day of staleness costs nothing.
Credentials are written from repository secrets and removed afterwards.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
git push
gh workflow run 'Rebuild tours from Bokun' --repo PerpetuaDev/zenrise-staging
sleep 45 && gh run list --workflow 'Rebuild tours from Bokun' --repo PerpetuaDev/zenrise-staging --limit 1
```

Expected: the run completes `success`. If it fails, read `gh run view --log-failed`.

---

### Task 11: Retirement sweep

Only after Tasks 6-9 are verified and the generated pages look right.

**Files:**
- Delete: `tour-kita-kamakura-hase.html`, `tour-tsurugaoka.html`, `tour-enoshima.html`, `tour-farmers-market.html`, `tour-zen-morning.html`, `tour-yokohama.html`
- Delete: `cms/tours-fixture.json`, `cms/tours-schema.json`, `cms/site-config-schema.json`, `cms/push-tours.py`, `cms/tour-routes.json`
- Modify: `lang.js` — remove superseded draft keys
- Modify: `cms/tours-setup.md` — rewrite for the Bokun pipeline
- Test: `cms/tests/test_no_orphans.py`

**Interfaces:** none.

- [ ] **Step 1: Write the failing test**

```python
# cms/tests/test_no_orphans.py
import glob, json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(p):
    with open(os.path.join(ROOT, p)) as f:
        return f.read()


class TestNoOrphans(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, 'cms', 'tours-config.json')) as f:
            cfg = json.load(f)
        self.slugs = {entry['slug'] for entry in cfg['tours'].values()}

    def test_only_generated_tour_pages_exist(self):
        on_disk = {os.path.basename(p)[len('tour-'):-len('.html')]
                   for p in glob.glob(os.path.join(ROOT, 'tour-*.html'))}
        self.assertEqual(on_disk, self.slugs)

    def test_retired_fixtures_and_schemas_are_gone(self):
        for p in ('cms/tours-fixture.json', 'cms/tours-schema.json',
                  'cms/site-config-schema.json', 'cms/push-tours.py',
                  'cms/tour-routes.json'):
            self.assertFalse(os.path.exists(os.path.join(ROOT, p)), p)

    def test_no_link_points_at_a_retired_tour_page(self):
        retired = ['kita-kamakura-hase', 'tsurugaoka', 'enoshima',
                   'farmers-market', 'zen-morning', 'yokohama']
        for page in glob.glob(os.path.join(ROOT, '*.html')):
            if 'archive' in page:
                continue
            body = read(os.path.basename(page))
            for slug in retired:
                self.assertNotIn(f'tour-{slug}.html', body,
                                 f'{os.path.basename(page)} links to retired tour-{slug}.html')

    def test_superseded_draft_lang_keys_are_gone(self):
        lang = read('lang.js')
        for key in ('tours_c1_', 'tours_d1_', 'rt04_'):
            self.assertNotIn(key, lang, key)

    def test_archive_is_untouched(self):
        self.assertTrue(os.path.exists(os.path.join(ROOT, 'archive/custom-booking/index.html')))
        self.assertIn("var RELAY_URL = ''", read('archive/custom-booking/index.html'))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest cms.tests.test_no_orphans -v`
Expected: FAIL on the hand-authored pages and retired fixtures still existing.

- [ ] **Step 3: Find every reference before deleting anything**

Run:
```bash
cd ~/projects/zenrise-staging
for s in kita-kamakura-hase tsurugaoka enoshima farmers-market zen-morning yokohama; do
  echo "== $s"; grep -rln "tour-$s" --include='*.html' --include='*.js' --include='*.py' --include='*.json' --include='*.md' . | grep -v '^./archive/' | grep -v '^./.git'
done
grep -rn 'tours_c[0-9]_\|tours_d[0-9]_\|rt04_' lang.js | wc -l
```
Expected: a list of referencing files, and a count of draft keys. Note them; every one must be handled in Step 4.

- [ ] **Step 4: Delete and clean up**

```bash
git rm tour-kita-kamakura-hase.html tour-tsurugaoka.html tour-enoshima.html \
       tour-farmers-market.html tour-zen-morning.html tour-yokohama.html
git rm cms/tours-fixture.json cms/tours-schema.json cms/site-config-schema.json \
       cms/push-tours.py cms/tour-routes.json
```

Then remove the superseded draft keys from `lang.js`. Delete only keys matching `tours_c<N>_*`, `tours_d<N>_*` and `rt04_*` in **both** the `en` and `ja` dictionaries. Keep every `tours_*` key that the generator emits (`tours_area_*`, `tours_len_*`, `tours_filter_*`, `nav_tours`, `home_tours_cta`, `td_*`) — the generator writes per-tour keys into each page's `ZENRISE_CMS_DICT`, not into `lang.js`.

Then rewrite `cms/tours-setup.md` to describe the Bokun pipeline: `--source bokun|cache`, `cms/tours-config.json`, the product list, the scheduled workflow, and the client-side steps that remain open (pricing two products, adding EN language, writing Japanese).

- [ ] **Step 5: Verify nothing broke**

Run: `python3 -m unittest discover -s cms/tests -t . -v`
Expected: all PASS, including `test_no_orphans`

Run: `python3 cms/build-tours.py --source cache && python3 cms/build-news.py`
Expected: both succeed

Run:
```bash
python3 -m http.server 8032 --bind 127.0.0.1 &
for p in index.html tours.html tour-ikebana-ichigo-ichie.html tour-zen-journey.html news.html about.html terms.html; do
  curl -s -o /dev/null -w "%{http_code}  $p\n" "http://127.0.0.1:8032/$p"
done
```
Expected: `200` for all seven

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Retire the hand-authored tours and the microCMS tours module

The six hand-authored tour pages, my draft tour copy in lang.js, the fixture,
and the tours/site-config schemas are all superseded: tours now generate from
Bokun, which is the single source. Two microCMS free-tier API slots stay spare
as a result.

Deleted only after the generated pages were verified, so nothing was removed
before its replacement was proven. archive/custom-booking/ is untouched.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: `/go/<slug>` redirects

**Files:**
- Create: `go/<slug>/index.html` for each tier product with a widget
- Delete: `go/kamakura/index.html`
- Modify: `cms/build-tours.py` — add `write_go_redirects(models)`
- Test: `cms/tests/test_go_redirects.py`

**Interfaces:**
- Consumes: `m['widgets']`, `m['id']`.
- Produces: `write_go_redirects(models) -> list[str]`.

`/go/kamakura` points at product `1272734`, which is OTA tier and not a site tour (spec 3.6). It is orphaned on-site, so it is deleted rather than migrated.

- [ ] **Step 1: Write the failing test**

```python
# cms/tests/test_go_redirects.py
import importlib.util, os, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_tours', os.path.join(ROOT, 'cms', 'build-tours.py'))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)

CH = 'e2350ad8-80af-4c18-a21a-acae6d72283f'


class TestRedirectHtml(unittest.TestCase):
    def test_redirects_to_the_widget_url(self):
        html = bt.go_redirect_html({'id': 's', 'full': True,
                                    'widgets': {'en': f'{CH}/experience-calendar/1'}})
        self.assertIn(f'https://widgets.bokun.io/online-sales/{CH}/experience-calendar/1', html)
        self.assertIn('http-equiv="refresh"', html)
        self.assertIn('location.replace', html)

    def test_is_noindex(self):
        html = bt.go_redirect_html({'id': 's', 'full': True, 'widgets': {'en': f'{CH}/x/1'}})
        self.assertIn('noindex', html)

    def test_no_page_without_a_widget(self):
        self.assertIsNone(bt.go_redirect_html({'id': 's', 'full': True, 'widgets': {}}))

    def test_no_page_for_an_unpriced_tour(self):
        self.assertIsNone(bt.go_redirect_html(
            {'id': 's', 'full': False, 'widgets': {'en': f'{CH}/x/1'}}))


class TestOtaRedirectRetired(unittest.TestCase):
    def test_go_kamakura_is_gone(self):
        self.assertFalse(os.path.exists(os.path.join(ROOT, 'go', 'kamakura', 'index.html')))

    def test_no_go_page_references_an_ota_product(self):
        ota = ['1272734', '1272756', '1272817', '1272825', '1272835', '1272849', '1273963']
        for dirpath, _, files in os.walk(os.path.join(ROOT, 'go')):
            for name in files:
                with open(os.path.join(dirpath, name)) as f:
                    body = f.read()
                for pid in ota:
                    self.assertNotIn(pid, body, f'{dirpath}/{name} references OTA product {pid}')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest cms.tests.test_go_redirects -v`
Expected: FAIL — `module 'build_tours' has no attribute 'go_redirect_html'`

- [ ] **Step 3: Implement**

```python
def go_redirect_html(m):
    """No-JS and email/social fallback: a bare redirect to the Bokun widget."""
    if not m.get('full'):
        return None
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
```

Call `write_go_redirects(models)` in `main()` after `write_tours_index(models)` and include the count in the final print.

- [ ] **Step 4: Retire the OTA redirect**

```bash
git rm -r go/kamakura
```

- [ ] **Step 5: Run tests and build**

Run: `python3 cms/build-tours.py --source cache && ls go/`
Expected: a directory per priced tour with a configured widget, and no `kamakura`

Run: `python3 -m unittest discover -s cms/tests -t . -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Generate /go/<slug> redirects, retire /go/kamakura

One redirect per priced tier tour, as the no-JS and email/social fallback.

/go/kamakura is deleted rather than migrated: it points at product 1272734,
which is OTA tier and therefore not a site tour under this design. It was created
on 8/19 before the tier decision and is orphaned on-site, so nothing internal
breaks. Recreate it manually if the URL turns out to have been shared externally.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Deliberately not in this plan

- **Spec section 5** — cookies section in `terms.html`, the consent decision, and
  reconciling the cancellation terms against what Bokun enforces per rate. These
  block *production*, not staging, and staging is `noindex`. They return when the
  port to zenrise.jp is scoped.
- **Removing the `Viator予約URL` field** from the live microCMS news schema
  (spec 6). That is a click in the microCMS UI, not code.
- **`contact.html`, `datepicker.js`, `relay/`** — deferred by decision, see spec
  section 7.
- **Per-language URLs and hreflang**, and Google Analytics on our own pages.

## Verification checklist

After Task 12, all of these must hold:

- [ ] `python3 -m unittest discover -s cms/tests -t . -v` — all tests pass
- [ ] `python3 cms/build-tours.py --source bokun` — succeeds against live Bokun, prints warnings only for known damage
- [ ] Exactly four `tour-*.html` files exist, matching the config slugs
- [ ] `tour-zen-journey.html` and `tour-swordsmithing.html` use the prep layout, carry no price and no widget
- [ ] `tour-ikebana-ichigo-ichie.html` shows `from ¥21,000 per adult` and mounts exactly one widget iframe
- [ ] No page outside `archive/` references a retired tour slug, `zenrise-booking-v1`, or `cal-go`
- [ ] `sitemap.xml` lists `tours.html` and all four tour pages
- [ ] `archive/custom-booking/` still loads and still has `RELAY_URL = ''`
- [ ] `contact.html`, `datepicker.js` and `relay/` are unmodified: `git diff --stat custom-booking-v1 -- contact.html datepicker.js relay/` is empty
- [ ] No Bokun credential string appears anywhere in the repo: `grep -ri "$(sed -n 's/^BOKUN_ACCESS_KEY=//p' ~/.bokun-api.env | tr -d '"')" . --exclude-dir=.git` returns nothing
