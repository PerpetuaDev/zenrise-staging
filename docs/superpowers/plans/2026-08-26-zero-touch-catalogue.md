# Zero-Touch Catalogue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** let the client add a tour in Bokun and have it appear correctly on the site with no code change.

**Architecture:** Four gates, all read from Bokun: `marketplaceVisibilityType == 'PRIVATE'` for tier, membership of a product list named `Website` for publication, an establishable slug, and completeness. Slugs derive from the English title under tested trim rules, then freeze in a committed registry so a live URL never churns. `number`, `area` and `length` derive too; `themes` stay manual because Bokun has no reliable source.

**Tech Stack:** Python 3 standard library only. No new dependencies — the repo has no package manifest and the scheduled Action must stay dependency-free.

**Spec:** `docs/superpowers/specs/2026-08-26-zero-touch-catalogue-design.md`

## Global Constraints

- **Staging only.** `zenrise-staging`. Nothing ships to zenrise.jp.
- 250 tests pass today (`python3 -m unittest discover -s cms/tests -t .`); all must still pass.
- Standard library only. Python 3.14.7. pytest is NOT available.
- Read-only Bokun calls. Never POST/PUT/PATCH/DELETE — and note the API has no write route anyway, verified.
- **The four existing slugs must not change**: `zen-journey`, `ikebana-ichigo-ichie`, `candle-making`, `swordsmithing`. A changed slug is a broken live URL.
- **No OTA product may ever render.** OTA ids: `1272734, 1272756, 1272817, 1272825, 1272835, 1272849, 1273963`.
- Tier product ids: `1273232` Ikebana, `1273235` candle-making, `1273194` Zen Journey, `1275339` Swordsmithing.
- Do NOT modify: `contact.html`, `datepicker.js`, `relay/`, `archive/`, `go/kamakura/`, `sitemap.xml`, `cms/bokun_client.py`, `cms/bokun_price.py`, `cms/bokun_labels.py`.
- Do NOT re-record fixtures in `cms/tests/data/`; build payloads synthetically.
- Do not suppress build output.
- Commit messages: imperative subject, "why" body, ending with exactly:
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`

---

### Task 1: slug derivation

**Files:**
- Create: `cms/tours_slug.py`
- Test: `cms/tests/test_tours_slug.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `slugify(text) -> str`, `derive(title) -> str`, `PLACES`, `FILLER`, `MAX_WORDS`.

The rules below are already tested against the client's real titles — reproduce them, do not redesign them.

- [ ] **Step 1: Write the failing test**

```python
# cms/tests/test_tours_slug.py
import unittest
from cms import tours_slug


class TestDerive(unittest.TestCase):
    def test_reproduces_the_hand_picked_slugs(self):
        cases = [
            ('The Zen Journey', 'zen-journey'),
            ('Ikebana Experience , “Ichigo Ichie”-KAMAKURA', 'ikebana-ichigo-ichie'),
            ('A private Japanese candle-making experience in Kamakura.', 'candle-making'),
        ]
        for title, want in cases:
            self.assertEqual(tours_slug.derive(title), want, title)

    def test_keeps_a_tour_name_that_follows_a_comma(self):
        # cutting at the comma would discard the distinctive part, and one real
        # title has a stray comma from a typo
        self.assertEqual(tours_slug.derive('Swordsmithing, “The Smith’s Flame”'),
                         'swordsmithing-smiths-flame')

    def test_only_drops_a_place_when_it_trails(self):
        # dropping place names anywhere turned this into "harbour"
        self.assertEqual(tours_slug.derive('Yokohama Harbour, After Dark'),
                         'yokohama-harbour-after-dark')

    def test_drops_repeated_trailing_places(self):
        self.assertEqual(tours_slug.derive('Zazen Morning in Kamakura Tokyo'),
                         'zazen-morning')

    def test_japanese_only_title_yields_nothing(self):
        for t in ('禅の旅', '横浜ナイトウォーク', ''):
            self.assertEqual(tours_slug.derive(t), '')

    def test_mixed_script_still_yields_something(self):
        # this is why an empty slug cannot be the "no English" detector
        self.assertEqual(tours_slug.derive('ZENの旅'), 'zen')

    def test_a_title_of_only_filler_keeps_its_words(self):
        self.assertEqual(tours_slug.derive('The Tour'), 'the-tour')

    def test_caps_at_four_words(self):
        self.assertEqual(
            tours_slug.derive('One Two Three Four Five Six'),
            'one-two-three-four')

    def test_slugify_strips_punctuation_and_accents(self):
        self.assertEqual(tours_slug.slugify('Wa-Rōsoku づくり'), 'wa-rosoku')
        self.assertEqual(tours_slug.slugify("Smith’s  Flame!"), 'smiths-flame')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `python3 -m unittest cms.tests.test_tours_slug -v`
Expected: `ModuleNotFoundError: No module named 'cms.tours_slug'`

- [ ] **Step 3: Implement**

```python
# cms/tours_slug.py
"""Derive a URL slug from a tour's English title.

Two rules were tried against the client's real titles and rejected. Cutting at
the first comma discarded "Ichigo Ichie", the distinctive half of one title, and
is unsafe besides because that title carries a stray comma from a typo. Dropping
place names wherever they appear turned "Yokohama Harbour, After Dark" into
"harbour". So: no comma cut, and a place name is dropped only when it trails.

See docs/superpowers/specs/2026-08-26-zero-touch-catalogue-design.md section 3.5.
"""
import re
import unicodedata

PLACES = ('kamakura', 'enoshima', 'yokohama', 'fujisawa', 'shonan', 'tokyo', 'hase')
FILLER = ('a', 'an', 'the', 'experience', 'experiences', 'tour', 'tours',
          'private', 'guided', 'japanese', 'in', 'of', 'with', 'and')
MAX_WORDS = 4


def slugify(text):
    s = unicodedata.normalize('NFKD', text or '')
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().replace('’', '').replace("'", '').replace('`', '')
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return re.sub(r'-{2,}', '-', s).strip('-')


def derive(title):
    words = [w for w in slugify(title).split('-') if w]
    if not words:
        return ''
    while len(words) > 1 and words[-1] in PLACES:
        words.pop()
    kept = [w for w in words if w not in FILLER] or words
    return '-'.join(kept[:MAX_WORDS])
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `python3 -m unittest cms.tests.test_tours_slug -v`
Expected: 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add cms/tours_slug.py cms/tests/test_tours_slug.py
git commit -m "Derive tour slugs from the English title

Rules tested against the client's real titles, reproducing three of the four
hand-picked slugs exactly. Records the two rejected rules: cutting at the first
comma discards the distinctive half of one title and is unsafe because that
title has a stray comma from a typo, and dropping place names anywhere turns
'Yokohama Harbour, After Dark' into 'harbour'.

A Japanese-only title derives to nothing, which is the correct failure — but a
mixed-script title like ZENの旅 derives to 'zen', which is exactly why an empty
slug cannot be used to detect a missing English translation.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: the slug registry

**Files:**
- Create: `cms/tours-slugs.json` (seeded, committed)
- Modify: `cms/tours_slug.py` (registry functions)
- Modify: `cms/tests/test_tours_slug.py`

**Interfaces:**
- Consumes: `derive` from Task 1; `tours_config.tour_entry` for overrides.
- Produces: `resolve(bokun_id, en_title, ja_title, languages, registry, override=None) -> (slug, reason)` and `load_registry(path)` / `save_registry(path, registry)`.

`reason` is a short string for logging: `'override'`, `'registry'`, `'derived'`, or a failure cause.

Precedence, highest first: **config override → registry → newly derived**. A slug once in the registry is never recomputed; that is the whole point.

Derivation is permitted only when BOTH hold:
- `'en'` is in `languages` (case-insensitive), AND
- the English title differs from the Japanese title

If a slug cannot be resolved, return `('', reason)` where reason names the missing piece.

- [ ] **Step 1: Write the failing test**

```python
# append to cms/tests/test_tours_slug.py
REG = {'1273194': 'zen-journey'}


class TestResolve(unittest.TestCase):
    def test_config_override_wins_over_everything(self):
        slug, why = tours_slug.resolve('1273194', 'The Zen Journey', '禅の旅',
                                       ['en', 'JA_JP'], REG, override='custom')
        self.assertEqual((slug, why), ('custom', 'override'))

    def test_registry_wins_over_derivation(self):
        # a retitled tour keeps its published URL
        slug, why = tours_slug.resolve('1273194', 'A Completely New Title', '禅の旅',
                                       ['en', 'JA_JP'], REG)
        self.assertEqual((slug, why), ('zen-journey', 'registry'))

    def test_derives_for_a_new_translated_tour(self):
        slug, why = tours_slug.resolve('999', 'Yokohama Harbour, After Dark',
                                       '横浜、夜の港をあるく', ['en', 'JA_JP'], REG)
        self.assertEqual((slug, why), ('yokohama-harbour-after-dark', 'derived'))

    def test_refuses_when_there_is_no_english_language_slot(self):
        slug, why = tours_slug.resolve('999', 'Some English Title', '日本語タイトル',
                                       ['JA_JP'], REG)
        self.assertEqual(slug, '')
        self.assertIn('language', why.lower())

    def test_refuses_when_the_slot_exists_but_is_unfilled(self):
        # both languages return the base content, so the titles match
        slug, why = tours_slug.resolve('999', 'Same Title', 'Same Title',
                                       ['en', 'JA_JP'], REG)
        self.assertEqual(slug, '')
        self.assertIn('translat', why.lower())

    def test_a_known_slug_is_returned_even_when_untranslated(self):
        # Ikebana's case: no en slot, but its slug is already settled
        reg = {'1273232': 'ikebana-ichigo-ichie'}
        slug, why = tours_slug.resolve('1273232', 'Ikebana', 'Ikebana',
                                       ['JA_JP'], reg)
        self.assertEqual((slug, why), ('ikebana-ichigo-ichie', 'registry'))

    def test_collision_gets_a_numeric_suffix(self):
        reg = {'111': 'zen-morning'}
        slug, why = tours_slug.resolve('222', 'Zen Morning', '禅の朝',
                                       ['en', 'JA_JP'], reg)
        self.assertEqual(slug, 'zen-morning-2')

    def test_registry_round_trips(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'r.json')
            tours_slug.save_registry(p, {'1': 'a-slug'})
            self.assertEqual(tours_slug.load_registry(p), {'1': 'a-slug'})

    def test_missing_registry_loads_empty(self):
        self.assertEqual(tours_slug.load_registry('/nonexistent/r.json'), {})
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `python3 -m unittest cms.tests.test_tours_slug -v`
Expected: `AttributeError: module 'cms.tours_slug' has no attribute 'resolve'`

- [ ] **Step 3: Implement, and seed the registry**

Add `load_registry`, `save_registry` and `resolve` to `cms/tours_slug.py`. Seed `cms/tours-slugs.json` with the four current slugs so no live URL changes:

```json
{
 "1273194": "zen-journey",
 "1273232": "ikebana-ichigo-ichie",
 "1273235": "candle-making",
 "1275339": "swordsmithing"
}
```

- [ ] **Step 4: Run and confirm**

Run: `python3 -m unittest cms.tests.test_tours_slug -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add cms/tours_slug.py cms/tours-slugs.json cms/tests/test_tours_slug.py
git commit -m "Freeze tour slugs in a committed registry

A slug derived on every build would change a live URL whenever the English title
was edited. So the first resolution is written to cms/tours-slugs.json and never
recomputed; a config override still wins over both.

Derivation requires an English language slot AND an English title that differs
from the Japanese, which together prove a real translation rather than the base
content being echoed back. But a tour whose slug is already known publishes
regardless — three of the four live tours have no en slot yet, and gating them on
translation would remove them for no benefit.

Seeded with the four current slugs so no live URL changes.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: catalogue resolution and the gates

**Files:**
- Modify: `cms/bokun_source.py` (`catalogue`, `fetch_records`)
- Modify: `cms/tours_config.py` (drop the allowlist requirement)
- Modify: `cms/tests/test_bokun_source.py`, `cms/tests/test_tours_config.py`

**Interfaces:**
- Consumes: `tours_slug.resolve`; `tours_config.ota_denylist`.
- Produces: `catalogue(client, cfg) -> list[int]` resolving by the gates, and per-tour hold-back decisions surfaced as warnings from `fetch_records`.

Gates, in order:

1. **Tier.** A product is a candidate only when `marketplaceVisibilityType == 'PRIVATE'`. The product search response may not carry that field — fetch the activity detail and read it there. Any id in `ota_denylist` is rejected outright regardless, as a second independent guard.
2. **Published.** If a product list whose title matches `productListName` (default `Website`, case-insensitive) exists, the catalogue is the intersection of its members with the PRIVATE set. **An empty list means publish nothing** — honour it, do not fall back. If no such list exists at all, fall back to `cfg['allowlist']` and warn that the fallback is in use.
3. **Sluggable.** Via `tours_slug.resolve`. A tour with no resolvable slug is held back with a warning naming the product title and the reason.
4. **Complete.** A tour with no cover photo, or no description, is held back with a warning. A tour with no price is NOT held back — it renders the in-preparation layout, which is existing behaviour.

Log the resolved catalogue on every run: the count, and each tour's id, slug and how the slug was resolved. A tour disappearing must be traceable.

- [ ] **Step 1: Write the failing tests**

Extend `cms/tests/test_bokun_source.py`'s `FakeClient` so it can serve a product list and per-product `marketplaceVisibilityType`. Cover: a PUBLIC product is excluded even if listed; a denylisted id is excluded even if PRIVATE and listed; an empty `Website` list yields nothing; a missing list falls back to the allowlist with a warning; a listed tour with no cover photo is held back with a warning naming it; a listed tour with no price is NOT held back.

- [ ] **Step 2: Run and confirm failure**

Run: `python3 -m unittest cms.tests.test_bokun_source -v`

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run the full suite**

Run: `python3 -m unittest discover -s cms/tests -t . -v`

- [ ] **Step 5: Commit**

---

### Task 4: derive number, area and length; wire the build

**Files:**
- Modify: `cms/bokun_source.py` (`to_record`)
- Modify: `cms/build-tours.py` if the record shape requires it
- Modify: the corresponding tests

Derivations:
- **`number`** — position in the registry's insertion order, formatted `%02d`. Stable once assigned; a new tour takes the next.
- **`area`** — `googlePlace.city` when present, else the trailing place name that Task 1's rules dropped from the title, else empty. An empty area must not crash `area_key()`; hold the tour back with a warning instead.
- **`length`** — from `durationText`, under five hours is Half-day. Promote the existing fallback to primary; a config value still overrides.
- **`themes`** — unchanged, still from config. A tour with none renders no theme chips.

A config entry remains optional throughout: a tour with no entry at all must build.

- [ ] **Step 1: Write the failing tests**
- [ ] **Step 2: Run and confirm failure**
- [ ] **Step 3: Implement**
- [ ] **Step 4: Verify against live Bokun**

Run: `python3 cms/build-tours.py --source bokun`

Expected: the resolved catalogue is logged; the three tours in the `Website` list build; the fourth is absent; every existing slug is unchanged; no OTA product appears.

- [ ] **Step 5: Commit**

---

## Verification checklist

- [ ] Full suite passes
- [ ] The four existing slugs are byte-identical to before
- [ ] The tour held out of the `Website` list does not render, and its absence is logged
- [ ] No OTA product renders; a denylisted id is refused even if listed
- [ ] An empty `Website` list publishes nothing rather than falling back
- [ ] `cms/tours-config.json`'s `allowlist` is now only a fallback, and the build works with a tour that has no config entry at all
- [ ] `archive/`, `contact.html`, `datepicker.js`, `relay/` unmodified
