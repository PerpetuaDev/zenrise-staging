# Bokun integration — design

Date: 2026-08-25
Status: approved for implementation on staging
Scope: `zenrise-staging` only. Nothing here ships to zenrise.jp without a separate
client-approval step.

## 1. Why

The client's JTB Bokun account is now the booking system. The site's own five-step
booking wizard has been archived (`archive/custom-booking/`, tag
`custom-booking-v1` on both repos) and is out of scope here.

The site must therefore:

- present the client's premium "Zenrise tier" tours from Bokun, and only those;
- send booking to Bokun rather than to our own form;
- keep the tour pages as the SEO surface, since Bokun's own widget pages are
  `noindex`.

## 2. Established facts

Verified against the live Bokun account (vendor `145344`, "ZENRISE") on 2026-08-25.
These are measurements, not assumptions.

**APIs.** Both work. Native REST authenticates with access key + secret over
HMAC-SHA1 (`X-Bokun-Date` + access key + method + path). OCTO works with a bearer
token at `https://api.bokun.io/octo/v1`. Native is far richer — 35KB for one
product versus 16KB for all eleven via OCTO — so **native is the content source
and OCTO is unused** (kept in the credentials file as a simpler fallback for
price/availability if ever wanted).

**Catalogue.** Eleven products exist. Four are Zenrise tier, confirmed by the
client:

| id | tour | priced | availability |
|---|---|---|---|
| 1273232 | Ikebana "Ichigo Ichie" | yes — ¥44,000 (1–2) / ¥21,000pp (3–6) | 45 slots/75d |
| 1273235 | Private candle-making | yes — ¥29,000 (1–2) / ¥12,000pp (3–4) | 42 slots/75d |
| 1273194 | The Zen Journey | **no price configured** | 74 slots/75d |
| 1275339 | Swordsmithing "The Smith's Flame" | **no price configured** | **0 slots** |

The other seven are OTA-styled and stay in Bokun for availability coordination.
They must never appear on the site.

**Pricing has two shapes.** Per passenger category (Adult / Child / Infant, from
`pricingCategories` joined to `pricePerCategoryUnit.id`) and per group-size tier
(`minParticipantsRequired`/`maxParticipantsRequired`). Both can apply at once.
There is no single price per tour. Prices are *not* channel-scoped — all four
channel-parameter variants return identical figures.

**The widget is a cross-origin iframe.** `BokunWidgetsLoader.js` injects an
`<iframe>` into `div.bokunWidget`. Consequences: our CSS and Adobe kit cannot
reach inside; Bokun's own custom CSS/SASS is the only styling route; the widget
centres a ~500px column and self-sizes (1252px tall for the calendar type). It
spawns three iframes — calendar, session, cart bubble.

**Widget language is baked into the widget, not the URL.** No `lang` parameter in
the snippet, and `?lang=`/`?language=` on the widget URL are ignored.

**Product content is single-language and mislabelled.** Every product reports
`languages: ['JA_JP']` with `baseLanguage: ja_JP`, and the English copy sits in
that Japanese slot. Only `durationText` localises (Bokun's own UI string). So
Bokun currently holds no Japanese product content at all.

**The widget loads third-party trackers** — Google Analytics, Mixpanel, Amplitude,
New Relic. Embedding it sets third-party cookies on zenrise.jp.

**Cancellation policies are inconsistent** — two products carry "Standard Viator
policy" (24h/100%), five "Non refundable", three bespoke named policies.
`terms.html` §02 states our own terms independently of these.

## 3. Architecture

**Bokun is the single source of tour content.** The tier products' Bokun copy is
already written in the Zenrise voice, so no editorial overlay is needed and
microCMS keeps only `news`. This avoids managing tour information in two places,
which was an explicit requirement.

**microCMS `tours` and `site-config` APIs are not created.** Two free-tier slots
stay spare. `cms/tours-schema.json` and `cms/site-config-schema.json` become dead
and are removed.

**Availability is never fetched in production.** It was only needed for our own
calendar, which is archived. The widget owns availability. The build reads
availability solely to derive prices.

Data flow:

```
Bokun native REST  ──►  cms/build-tours.py --live  ──►  tour-<slug>.html   (one per tier product)
   product list                 │                        tours.html        (CMS:tours-grid markers)
   + activity detail            │                        index.html        (CMS:home-tours markers)
   + availabilities (price)     │
                                └──►  cms/tours-cache.json  (committed, so builds are reproducible
                                                             and a Bokun outage cannot empty the site)
```

### 3.1 Which products to render

Ordered resolution, first hit wins:

1. A Bokun **product list** named `Website` — `/product-list.json/list` then
   `/product-list.json/{id}`. The endpoint is live and currently returns `[]`
   because none exist. When the client creates one, they control the site's
   catalogue from Bokun with no code change. This is the target mechanism.
2. An explicit id allowlist in `cms/tours-config.json` — the four ids above.
   This is the interim mode, so implementation is not blocked on the client.

Never fall back to "all products": that would publish the OTA tours.

The `TAILOR_MADE` attribute correlates with the tier but covers only two of the
four (candle-making and swordsmithing carry no taxonomy at all), so it is not
usable as the filter. Recorded here so nobody tries it later.

### 3.2 URLs and slugs

Bokun has no slug field, and deriving slugs from titles would churn URLs whenever
the client edits a title. So `cms/tours-config.json` holds an explicit
`bokunId → slug` map. Slugs are permanent once published.

The six hand-authored `tour-*.html` pages never reached production, so no
redirects are needed.

### 3.3 Normalisation

Bokun text is dirty. The build must, in this order:

1. decode HTML entities (`&#34;`, `&#39;`, `&nbsp;` all appear in live copy);
2. strip tags, preserving paragraph breaks;
3. collapse runs of whitespace.

The build must **not** attempt to repair mangled prose. Live copy contains
intra-word spacing damage (`templ e`, `wa l ked`, `S eated fore t`) and a stray
"PDF" mid-sentence, apparently from a PDF paste. The build **warns** on suspected
damage — a lone one- or two-letter token between two words — and renders the text
as-is. Guessing would corrupt content silently. Fixing the source is the client's
editorial job and does not block this work.

`excerpt` is not reliably a lede: Swordsmithing's is a styled eyebrow
("24TH-GENERATION SMITH · LINEAGE OF MASAMUNE · KAMAKURA"). Templates use
`excerpt` for the card line only, never as the detail-page lede, which comes from
`description`.

### 3.4 Field mapping

| Surface | Source |
|---|---|
| card + detail title | `title` |
| card line | `excerpt` |
| detail lede and body | `description` |
| route/itinerary table | `agendaItems[].title` + `.body` (duration prefixes like "30min" stay in the body for now) |
| cover and gallery | `photos[].originalUrl` via `imgcdn.bokun.tools` |
| duration chip | `durationText` |
| group size | rate `minPerBooking`/`maxPerBooking` |
| price | see 3.5 |
| area | `googlePlace.city`, falling back to `area` in `cms/tours-config.json` (3.9) |

### 3.5 Price display

Cards and tiles show **"from ¥X per adult"**, where X is the lowest Adult-category
price across all group tiers — ¥21,000 for Ikebana, ¥12,000 for candle-making.
If a product has no Adult category, X is the lowest price of any category and the
label drops "per adult" rather than inventing a category name.

Detail pages show the full breakdown: every category and every group tier.

A product with no price resolves to the **in-preparation** layout
(`cms/templates/tour-prep.html`), with no price and no widget. That covers The Zen
Journey and Swordsmithing today, and the five in-preparation variants built on
8/11 are reused as intended rather than discarded.

Prices are baked at build time so they are in our HTML for search engines. Drift
is bounded by the scheduled rebuild (3.7).

### 3.6 Booking path

Tour detail pages embed the Bokun **calendar widget** for that product, styled via
Bokun's custom CSS to the site palette:

```
Primary   #294138      Secondary #F7F4EA
hover     #1F3328      panel     #EDE9E5
selected date  bg #294138 / text #F7F4EA
available      text #294138 on #F7F4EA, border rgba(41,65,56,0.14)
in-range wash  rgba(41,65,56,0.06)
disabled/past  rgba(41,65,56,0.28)
```

Typography will not match — the iframe cannot load our domain-scoped Adobe kit.
Two prerequisites could fix it (add `widgets.bokun.io` to the kit's allowed
domains, and `@import` the kit inside Bokun's custom CSS); both are unverified, so
the design assumes mismatched type and treats matching it as an enhancement.

`/go/<slug>` redirect pages are kept as the no-JS and email/social fallback, one
per tier product, extending the existing `/go/kamakura`. Note that page currently
points at channel `e2350ad8-…` while the calendar widget uses `6db7a498-…`;
implementation must settle on one channel so attribution is consistent.

**Bilingual booking is unresolved and needs one panel check.** Because language is
baked per widget, a bilingual site needs either a `lang` option in the widget
builder (one widget per product) or two widgets per product. Until that is known
the build reads widget ids from `cms/tours-config.json` as
`{ bokunId: { en: "<uuid>/<type>/<id>", ja: "…" } }`, with `ja` falling back to
`en`. That shape works either way and costs nothing if one widget turns out to
suffice.

### 3.7 Build and refresh

`cms/build-tours.py` gains a real `--live` mode against Bokun, replacing the
fixture. Existing behaviour is kept: marker-region injection into `tours.html` and
`index.html`, per-page `ZENRISE_CMS_DICT`, sitemap regeneration.

Bokun cannot call a webhook at us, so a **scheduled GitHub Action** rebuilds
(daily is enough — prices and copy change rarely; availability is live in the
widget and never baked). The existing microCMS webhook keeps driving news
rebuilds.

`cms/tours-cache.json` is committed on every successful build. If Bokun is
unreachable the build uses the cache and warns, so an API outage can never empty
the tours pages.

### 3.8 Filtering and scale

The tours-index filters (area / theme / length) are retained at full generality
even though four products barely need them — the client expects to add Zenrise-tier
tours soon. Noted as deliberately over-specified for the current catalogue.

### 3.9 `cms/tours-config.json`

One file holds everything the build needs that Bokun cannot express. It is the
only hand-maintained input, and it is small by design.

```json
{
  "productListName": "Website",
  "allowlist": [1273232, 1273235, 1273194, 1275339],
  "tours": {
    "1273232": {
      "slug": "ikebana-ichigo-ichie",
      "area": "Kamakura",
      "jaReviewed": false,
      "widgets": { "en": "<channelUUID>/experience-calendar/1273232" }
    }
  }
}
```

- `productListName` — the Bokun product list to prefer (3.1).
- `allowlist` — interim catalogue until that list exists. Never empty; an empty
  allowlist with no product list is a build error, not a licence to render
  everything.
- `slug` — permanent URL segment. Never derived from the title.
- `area` — overrides `googlePlace.city`, which is absent on some products.
- `jaReviewed` — the gate in section 4. `false` means the build renders English
  for that product even in Japanese pages. A human sets this to `true` only after
  reading the Japanese in Bokun. The build never sets it.
- `widgets` — widget path per language; `ja` falls back to `en` when absent.

A tier product present in the catalogue but missing from `tours` is a build
error: it would otherwise get an unstable URL.

## 4. Bilingual and SEO

EN-first, per the standing priority.

Japanese tour content does not exist in Bokun and cannot be invented here. The
client's path is: add `EN` to each product and move the existing English into it,
then write Japanese into the `JA_JP` slot. Machine translation is acceptable as a
Bokun-side draft but must not reach the site — the build renders Japanese only for
products whose `jaReviewed` flag is `true` in `cms/tours-config.json` (3.9), so raw
MT cannot leak onto a premium site.

Until then, JA visitors see Japanese site chrome (from `lang.js`) around English
tour content, which is the status quo for the rest of the site.

Per-language URLs and hreflang remain a separate, client-approved round. This
design does not preclude them: generated pages can emit `/ja/` variants when the
content exists.

In scope here: `Product`/`Tour` JSON-LD per tour page with price and currency,
canonical tags, sitemap entries, and unique titles and descriptions per tour.

## 5. Cookies, consent and terms

**Blocking for embedding, not for building.** Pages can be built and reviewed on
staging first; the embed must not reach production until this is resolved.

- `terms.html` needs its cookies section. The condition set at launch — "if/when
  cookies are used" — is now met by the widget's trackers.
- Whether consent gating is required (JP APPI plus European visitors) is a client
  decision with legal input. Staging is `noindex` and not a live sales channel, so
  it can carry the embed while that is settled.
- `terms.html` §02 cancellation terms must be reconciled with what Bokun actually
  enforces per rate. Five products are "Non refundable", which is a harder promise
  than the page currently makes, and two carry a Viator-authored policy. This has
  特商法 implications and is a client conversation, not a copy edit.

## 6. Retirement

Once the generated pages are verified on staging:

- delete the six hand-authored `tour-*.html` pages and the tours fixture;
- delete my draft `tours_*` / `d*` / `rt04_*` lang keys, which are superseded by
  Bokun copy (JA route-stop keys from the client's booklet are worth keeping until
  Japanese exists in Bokun);
- delete `cms/tours-schema.json`, `cms/site-config-schema.json`,
  `cms/push-tours.py`, `cms/tours-fixture.json`, `cms/tour-routes.json`;
- remove the `Viator予約URL` field from the live microCMS news schema.

## 7. Open items

Client-dependent, none blocking implementation on staging:

1. Price The Zen Journey; configure Swordsmithing (no price, no availability).
2. Create the `Website` product list in Bokun.
3. Add `EN` language per product; move English across; write Japanese.
4. Decide on cookie consent; reconcile cancellation terms.
5. Fix the mangled prose in Bokun.
6. Decide the voice question for OTA-tier copy — does not affect this build.

Needs one panel check by us: whether the widget builder emits a `lang`
parameter, and which booking channel the site should use.

Undecided and deferred: what becomes of `contact.html`'s enquiry flow. The relay
and its bilingual emails still work, and a general enquiry route for bespoke
requests has obvious value alongside Bokun booking. Recommendation is to keep it
and revisit once the tour pages are real, rather than fold that decision into this
one.

## 8. Out of scope

The archived custom booking flow; per-language URLs and hreflang; Google
Analytics on our own pages (thread C); porting any of this to production.
