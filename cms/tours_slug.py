"""Derive and freeze the URL slug for a tour.

Two rules were tried against the client's real titles and rejected. Cutting at
the first comma discarded "Ichigo Ichie", the distinctive half of one title, and
is unsafe besides because that title carries a stray comma from a typo. Dropping
place names wherever they appear turned "Yokohama Harbour, After Dark" into
"harbour". So: no comma cut, and a place name is dropped only when it trails.

Freezing matters more than deriving. A slug recomputed on every build would
change a live URL whenever the English title was edited, so the first resolution
is written to the registry and never recomputed.

See docs/superpowers/specs/2026-08-26-zero-touch-catalogue-design.md sections
3.3 and 3.5.
"""
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(HERE, 'tours-slugs.json')

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
    """A trimmed slug from an English title, or '' when nothing usable remains."""
    words = [w for w in slugify(title).split('-') if w]
    if not words:
        return ''
    while len(words) > 1 and words[-1] in PLACES:
        words.pop()
    kept = [w for w in words if w not in FILLER] or words
    return '-'.join(kept[:MAX_WORDS])


def load_registry(path=None):
    try:
        with open(path or REGISTRY_PATH) as f:
            return {str(k): v for k, v in json.load(f).items()}
    except (OSError, ValueError):
        return {}


def save_registry(path, registry):
    with open(path or REGISTRY_PATH, 'w') as f:
        json.dump({str(k): v for k, v in sorted(registry.items())},
                  f, ensure_ascii=False, indent=1)
        f.write('\n')


def _has_english(languages):
    return 'en' in [str(x).lower() for x in (languages or [])]


def _unique(slug, bokun_id, registry):
    taken = {v for k, v in registry.items() if str(k) != str(bokun_id)}
    if slug not in taken:
        return slug
    n = 2
    while f'{slug}-{n}' in taken:
        n += 1
    return f'{slug}-{n}'


def resolve(bokun_id, en_title, ja_title, languages, registry, override=None):
    """(slug, reason) for a tour. reason is for logging, not display.

    Precedence: a config override, then the frozen registry, then a fresh
    derivation. Derivation is the only path that requires a translation, because
    it is the only path that reads the English title -- a tour whose slug is
    already settled publishes regardless of its translation state.
    """
    key = str(bokun_id)
    if override:
        return override, 'override'
    if registry.get(key):
        return registry[key], 'registry'
    if not _has_english(languages):
        return '', 'no English language slot on the product yet'
    if (en_title or '').strip() == (ja_title or '').strip():
        return '', 'English slot exists but the title is not translated yet'
    slug = derive(en_title)
    if not slug:
        return '', 'the English title yields no usable slug'
    return _unique(slug, key, registry), 'derived'
