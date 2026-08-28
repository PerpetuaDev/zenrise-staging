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
    """A tour's hand-written config, or {} when it has none at all.

    A config entry is now OPTIONAL (zero-touch catalogue, spec 3.6): the slug,
    number and area all have a derivation path of their own (see
    bokun_source.fetch_records), so a tour the client adds in Bokun and never
    touches in tours-config.json must still build. This no longer requires a
    'slug' key either -- a present entry with no slug simply carries no slug
    override (derivation or the registry take over), while any other
    hand-written fields (themes, widgets, ...) still apply.
    """
    tours = cfg.get('tours') or {}
    if str(bokun_id) in tours:
        return tours[str(bokun_id)]
    if bokun_id in tours:
        return tours[bokun_id]
    return {}


def corrections(cfg):
    return cfg.get('corrections') or {}


def ota_denylist(cfg):
    return [int(i) for i in (cfg.get('otaDenylist') or [])]
