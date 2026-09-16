# zenrise-staging

The Zenrise rebuild that became the live site. **Dormant since 2026-09-16.**

## Status

`PerpetuaDev/zenrise` is the live site (`zenrise.jp`) and the only repo that
should be changed. This tree was adopted there wholesale on 2026-09-11
(`13f16e1`), and both repos were brought level again on 2026-09-16.

Staging stays here for the next change big enough to want a client review pass
before it goes live. Until then nothing here is published anywhere that matters:
it is a project page (`perpetuadev.github.io/zenrise-staging/`) serving
`robots.txt: Disallow: /`.

## This repo is not a branch of the live one

There is **no common ancestor** -- `git merge-base` returns nothing. Staging is
adopted wholesale, never merged. Read the live repo's `CLAUDE.md` for the
invariants an adoption silently reverts (`CNAME`, `robots.txt`, the GA tag, the
push-race retry loop, `relay/`).

## Waking it up

1. Uncomment the `schedule:` block in `.github/workflows/build-tours.yml`.
2. Check `BOKUN_*` and `MICROCMS_*` secrets are still valid.
3. Rebase onto whatever the live repo has published since, or the next adoption
   will revert it.

Both build scripts still work on manual dispatch while dormant.

## Tests

`python3 -m pytest cms/tests` -- 482 tests. Both build workflows now run them
(via `python3 -m unittest discover -s cms/tests -t .`, so the runner needs no
install), after the build and before the commit.
