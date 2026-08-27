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


def records_with_fallback(fetch, client, cfg, cache_path=None, require_live=False):
    """Fetch from Bokun; on failure fall back to the committed cache.

    An API outage must never empty the tours pages.

    require_live turns that fallback off. Unattended builds need it: a silent
    cache rebuild produces no diff, so a scheduled job with wrong credentials
    would report "no changes to publish" on every run and look healthy while
    publishing nothing at all.
    """
    try:
        records, warnings = fetch(client, cfg)
    except Exception as e:
        if require_live:
            raise
        cached = read_cache(cache_path)
        if cached is None:
            raise
        return cached, [f'Bokun fetch failed ({e}); built from cache '
                        f'{cache_path or CACHE_PATH}. Prices may be stale.']
    write_cache(cache_path, records)
    return records, warnings


def load_records(source='bokun', cache_path=None, require_live=False):
    from . import bokun_client, bokun_source, tours_config
    cfg = tours_config.load()
    if source == 'cache':
        cached = read_cache(cache_path)
        if cached is None:
            raise RuntimeError('no tours cache to build from')
        return cached, cfg, ['built from cache by request']
    elif source == 'bokun':
        client = bokun_client.from_env()
        records, warnings = records_with_fallback(
            bokun_source.fetch_records, client, cfg, cache_path,
            require_live=require_live)
        return records, cfg, warnings
    else:
        raise ValueError(f'unknown --source {source!r}; must be "bokun" or "cache"')
