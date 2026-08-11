# Tours CMS module — setup

Pipeline mirrors the news section. Current state: **fixture mode** — pages are
generated from `cms/tours-fixture.json`; no microCMS `tours` API exists yet.

## Build (works today)

    python3 cms/build-tours.py            # fixture mode
    python3 cms/build-tours.py --live     # from microCMS, once the API exists

Outputs: `tour-<id>.html` ×N (full detail when `ledeJa/En` is set, otherwise the
"in preparation" layout), the card grid in `tours.html`, and the homepage tiles
in `index.html` — the latter two between `CMS:tours-grid` / `CMS:home-tours`
markers. Per-tour bilingual copy travels in each page's `ZENRISE_CMS_DICT`.

## Going live (microCMS UI steps, in order)

1. Create list API `tours` — import `cms/tours-schema.json`.
   If the `select` fields fail to import, recreate エリア / テーマ / 形式 by hand
   with exactly the values in the schema file (they drive the page filters).
2. Create object API `site-config` — import `cms/site-config-schema.json`
   (注目ツアー = relation to tours; スライドショー画像 = 複数画像).
   This uses the free plan's third and final API slot.
3. Seed content: `python3 cms/push-tours.py`, then upload covers to microCMS
   media and attach them to each tour (fixture covers are interim site photos).
4. Delete the news API's now-unused `Viator予約URL` field while in the UI.
5. Add a microCMS webhook for `tours` (and `site-config`) pointing at the same
   GitHub Action as news; extend the workflow to run `build-tours.py --live`.

## v2 (deferred)

- Route/pamphlet stops as a repeater + custom field — today only No. 04 has a
  pamphlet; its stops ship in `cms/tour-routes.json` keyed by tour id.
- Homepage news section (`CMS:home-news` markers in index.html) wired into
  build-news.py so the latest three articles inject automatically.
- Hero slideshow images from site-config.
