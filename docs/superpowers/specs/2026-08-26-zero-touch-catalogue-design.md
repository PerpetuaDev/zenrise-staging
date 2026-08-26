# Zero-touch catalogue — design

Date: 2026-08-26
Status: approved for implementation on staging
Scope: `zenrise-staging` only.
Supersedes: the hand-maintained `allowlist` and `tours[].slug` entries in
`cms/tours-config.json` established by the Bokun integration
(`docs/superpowers/specs/2026-08-25-bokun-integration-design.md`, sections 3.1
and 3.2).

## 1. Why

Adding a tour currently needs a developer. The catalogue is a hardcoded id
allowlist, and every tour needs a hand-written config entry carrying a slug, a
number, an area, a length and a theme list — or the build fails, by design, to
stop a tour getting an unstable URL.

That directly contradicts the client-self-serve goal: the client should be able to
add a tour in Bokun and have it appear, correctly, with no code change. It also
sets a trap for the scheduled rebuild — once a `Website` product list exists and
the client adds a tour to it, today's build would *fail* until someone edits
config.

Everything needed to fix this turns out to be in Bokun already.

## 2. What Bokun tells us, verified

Measured against the live account (vendor 145344) on 2026-08-26.

**Tier separation is explicit.** `marketplaceVisibilityType` is `PRIVATE` on all
four Zenrise-branded tours and `PUBLIC` on all seven OTA tours. It maps exactly to
the split, and it is far more reliable than what the integration currently infers
from cancellation-policy naming or the `TAILOR_MADE` attribute.

**There is no native readiness state.** `published` is `False` on all eleven
products, including the OTA ones that are demonstrably live, so it does not mean
what its name suggests and cannot gate anything. No other field separates
finished tours from work in progress.

**Syndication exposure is narrow.** `externalId` is set on exactly one product
(the Viator-syndicated `1272734`), and `storedExternally` is false everywhere.

**No product lists exist yet**, so the list mechanism is greenfield.

**`externalId` is not visible in the vendor panel**, so it cannot serve as a
client-editable slug override. Checked with the user.

## 3. Four gates

A tour reaches the site only when all four hold. Each is visible in Bokun, and
none requires a code change.

| gate | source | fails how |
|---|---|---|
| 1. Zenrise tier | `marketplaceVisibilityType == 'PRIVATE'` | a PUBLIC tour is never rendered |
| 2. Published | member of the `Website` product list | omitted tours are invisible, silently and correctly |
| 3. Translated | `'en' in languages` AND the English title differs from the Japanese | held back, with a warning naming the product |
| 4. Complete | has a price, a cover photo and a description | held back, or renders the in-preparation layout — see 3.4 |

### 3.1 Tier — `PRIVATE`

The catalogue is every product whose `marketplaceVisibilityType` is `PRIVATE`.
The existing `otaDenylist` stays as a belt-and-braces guard: cheap, and it keeps
the property that publishing an OTA tour requires two independent mistakes.

This inverts one failure mode and that is worth stating plainly: today,
forgetting config means a tour silently does not appear; under this design,
switching a tour to `PUBLIC` in Bokun silently *removes* it from the site. If the
client ever wants a Zenrise tour sold through OTAs as well, that will surprise
them. The build therefore logs the catalogue it resolved on every run, so a
disappearance is traceable.

### 3.2 Published — the `Website` product list

A Bokun product list is a named collection of products, maintained in the panel.
`/product-list.json/list` exposes them; none exist yet.

Membership of a list named `Website` is the publish gate. It gives the client a
real draft state: build the tour in Bokun over days, add it to the list when it is
ready. It fails safe — forgetting to add a tour means it does not appear, rather
than a half-finished page going live.

Until the list exists, the build falls back to the config `allowlist` so nothing
breaks. Once it exists, the list wins. If the list exists but is empty, that is
an explicit "publish nothing" and must be honoured, not treated as a fallback
trigger.

### 3.3 Translated — the slug precondition

Slugs derive from the English title (3.5), so a tour cannot be published before
it has one. Detecting that reliably is subtler than it looks.

**Do not use "the slug came out empty" as the detector.** It only works if
Japanese titles contain no Latin characters, and they frequently do. Measured:
`ZENの旅` slugifies to `zen`, `Ikebana体験「一期一会」` to `ikebana`, `鎌倉ZEN散歩` to
`zen`. Each would generate and then permanently freeze a URL derived from
untranslated content.

The detector is instead:

- `'en'` present in the product's `languages`, AND
- the `?lang=EN` title differs from the `?lang=ja` title

Both are required. The language slot alone is insufficient: a slot can exist
unfilled, in which case both languages return the base content and the titles
match. Three of the four current products show the mirror-image case — no `en`
slot, yet `?lang=EN` returns full English, because the authored English still sits
in the `JA_JP` base slot. That is harmless today and becomes wrong the moment the
base is replaced with Japanese.

A tour failing this gate is held back with a warning naming the product and the
missing piece. The warning must be legible: a held-back tour reads as "the site is
broken" otherwise.

### 3.4 Complete — the safety net

Gate 2 is a deliberate human act, but it does not prevent listing a tour that is
not finished. A tour must additionally have a price, a cover photo and a
description.

A tour that is listed and translated but lacks a **price** renders the
in-preparation layout, which is existing behaviour and correct — it is a real
page for a real tour that cannot yet be booked. A tour lacking a **cover photo or
description** is held back entirely, because those produce a visibly broken page
rather than an incomplete one.

### 3.5 Slugs

Derived from the English title, trimmed, then **frozen**.

Rules, in order:

1. Transliterate and lowercase; strip apostrophes and smart quotes; replace any
   run of non-alphanumerics with a single hyphen.
2. Drop a trailing place name, repeatedly: `kamakura`, `enoshima`, `yokohama`,
   `fujisawa`, `shonan`, `tokyo`, `hase`.
3. Drop filler words anywhere: `a`, `an`, `the`, `experience`, `experiences`,
   `tour`, `tours`, `private`, `guided`, `japanese`, `in`, `of`, `with`, `and`.
4. Cap at four words.
5. If the result collides with an existing slug, append `-2`, `-3`, and so on.

Two rules were tried and rejected against real titles: **cutting at the first
comma** discarded the distinctive part of "Ikebana Experience , “Ichigo
Ichie”-KAMAKURA" and is unsafe because one title has a stray comma from a typo;
and **dropping place names anywhere** turned "Yokohama Harbour, After Dark" into
`harbour`.

Measured against the four real titles, this reproduces three of the four
hand-picked slugs exactly:

| English title | derived | hand-picked |
|---|---|---|
| The Zen Journey | `zen-journey` | same |
| Ikebana Experience , “Ichigo Ichie”-KAMAKURA | `ikebana-ichigo-ichie` | same |
| A private Japanese candle-making experience in Kamakura. | `candle-making` | same |
| Swordsmithing, “The Smith’s Flame” | `swordsmithing-smiths-flame` | `swordsmithing` |

**Freezing.** On first publish the derived slug is written to a registry and never
recomputed. Without this, editing an English title would silently change a live
URL. The registry is `cms/tours-slugs.json`, keyed by Bokun product id, written by
the build and committed like `cms/tours-cache.json`.

**Override.** An explicit `slug` in a `cms/tours-config.json` tour entry always
wins over both the registry and the derivation. This is the escape hatch for a
mangled slug — a developer edit, expected to be rare, per the user. The four
existing slugs are seeded into the registry so no current URL changes.

### 3.6 The other config fields

`number`, `area`, `length` and `themes` are hand-written today and must also
derive, or adding a tour still needs a developer:

- **`number`** — the "Tour No. NN" eyebrow. Assign by the registry's insertion
  order, so numbers are stable once assigned and a new tour takes the next one.
- **`area`** — `googlePlace.city` when present, else the trailing place name
  dropped from the title in 3.5 step 2, else held back. Currently absent on most
  tier products, so the title is the practical source.
- **`length`** — derived from `durationText`: under five hours is Half-day. The
  existing derivation, promoted from fallback to primary.
- **`themes`** — no reliable Bokun source. `activityCategories` is OTA taxonomy
  (`THEME_PARKS`, `CITY_BREAK`) and absent on two of four tier products.
  **Themes stay manual**, and a tour with none simply carries no theme chips. This
  is the one field that cannot go zero-touch, and it is honest to say so: a new
  theme needs a Japanese label authored by a human.

## 4. What is still manual after this

- **Themes**, per 3.6.
- **A mangled slug**, via the config override.
- **Chip labels** for any Bokun enum value beyond the 22 mapped, which warn.
- All Bokun content authoring, which is the point.

## 5. Out of scope

`activityAttributes`; the `supportedAccessibilityTypes` field; surfacing
`bookableExtras` (the ¥10,000 per-guest arrangement fee); reconciling
`terms.html` against Bokun's per-rate cancellation policies; and the port to
production.
