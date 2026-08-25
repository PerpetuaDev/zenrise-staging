# Archive

## `custom-booking/` — the bespoke Zenrise booking flow

A frozen, runnable snapshot of the five-step booking wizard we designed and
built before the client's JTB Bokun account became the booking system.

It is kept for two reasons: it is the version we want available for the case
study, and it is the design we intend to return to if the client's plan is ever
upgraded to one that permits a custom front end against the Bokun API.

**Live at** `/archive/custom-booking/` on the staging site. The whole point of
the frozen copy is that it stays reachable *after* the real pages move to Bokun,
so the two can be compared side by side.

### What's in here

| File | What it is |
|---|---|
| `index.html` | `contact.html` as it stood — the five-step wizard, steps 1–5 plus the sent view |
| `tour-kita-kamakura-hase.html` | tour detail page with the sticky availability calendar |
| `datepicker.js` | the range-mode date picker (one calendar, pick start/end) |
| `lang.js` | the EN/JA dictionary + injected nav, as of the snapshot |
| `assets/`, favicons | the photography and icons these two pages reference |

The full designed journey works end to end: open the tour page, pick a date on
the calendar, hand off to the wizard with region/length/dates prefilled, step
through to the confirmation screen.

Files are duplicated rather than shared with the live pages on purpose — an
archive that reads its neighbours' `lang.js` stops being a snapshot the first
time someone edits it.

### Deliberate differences from the original

- **Sends no mail.** `RELAY_URL` is set to `''`, which the flow already
  supported as a front-end-only mode: the Send button goes straight to the sent
  view without calling the DigitalOcean relay. The original posted to the relay,
  which mailed `hello@zenrise.jp` and the customer. You can reach the
  confirmation screen as often as you like without mailing the client.
- **`noindex, nofollow`**, and sibling nav/footer links point out at the parent
  staging site. The `contact.html` link points at this directory's own
  `index.html`, so the wizard's active-nav state still behaves.
- Nothing else is changed. No banner, no watermark, no dev badge — the pixels
  are the pixels, so screenshots are clean.

### Known cosmetic gap

The route table's per-stop thumbnails reference
`assets/tours/04-kita-kamakura-hase/*.jpg`, which never existed — real stop
photography was still pending when the snapshot was taken. Those slots render as
their placeholder treatment, exactly as they did at the time.

### Running it

    python3 -m http.server 8009 --bind 127.0.0.1
    # → http://127.0.0.1:8009/archive/custom-booking/

Fonts come from Adobe kit `kty6qoz`, which is domain-scoped — they resolve on
`127.0.0.1` and on the staging domain.

### Restore points

The frozen copy is for looking at. To *work* on this code again, check out the
tags — they hold the real, integrated version rather than a copy with its nav
rewritten:

- `custom-booking-v1` on **`zenrise-staging`** — the richer version: the wizard
  alongside the tours pages and the calendar → wizard handoff.
- `custom-booking-v1` on **`zenrise`** (production) — the wizard as it was
  actually deployed to zenrise.jp, plus the relay function source at
  `relay/packages/zenrise/booking/index.js` and its Mailgun bilingual emails.
