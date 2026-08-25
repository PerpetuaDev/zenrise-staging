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
