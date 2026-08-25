"""Normalise Bokun product copy.

Bokun text arrives with HTML entities, markup, and spacing damage consistent
with machine translation or a PDF paste. Corrections are a reviewed map rather
than an algorithm: the whole tier corpus holds only four damage sites, and no
word list exists on the build machine to validate a rejoin against. See spec
section 3.3.
"""
import html
import re

_BLOCK = re.compile(r'(?i)</(?:p|div|li|h[1-6])\s*>|<br\s*/?>')
_TAG = re.compile(r'<[^>]+>')
_WS = re.compile(r'[^\S\n]+')

# Genuine one- and two-letter English words, so the damage detector does not
# flag ordinary prose.
_SHORT_WORDS = {
    'a', 'i', 'am', 'an', 'as', 'at', 'be', 'by', 'do', 'go', 'he', 'hi', 'if',
    'in', 'is', 'it', 'me', 'my', 'no', 'of', 'oh', 'ok', 'on', 'or', 'so',
    'to', 'up', 'us', 'we',
}

# word, stray 1-2 letter token, word
_DAMAGE = re.compile(r'\b([A-Za-z]{2,})\s+([A-Za-z]{1,2})\s+([A-Za-z]{2,})\b')


def _decode(raw):
    text = html.unescape(raw or '')
    # html.unescape turns &nbsp; into U+00A0. Written as an escape on purpose:
    # a literal non-breaking space in source is invisible and unmaintainable.
    return text.replace('\u00a0', ' ')


def _apply_corrections(text, corrections):
    for bad, good in (corrections or {}).items():
        text = text.replace(bad, good)
    return text


def _warn(text):
    warnings = []
    for m in _DAMAGE.finditer(text):
        if m.group(2).lower() in _SHORT_WORDS:
            continue
        warnings.append(
            f'suspected spacing damage, not covered by corrections: {m.group(0)!r}')
    return warnings


def clean(raw, corrections=None):
    text = _decode(raw)
    text = _BLOCK.sub(' ', text)
    text = _TAG.sub(' ', text)
    text = _apply_corrections(text, corrections)
    text = _WS.sub(' ', text).replace('\n', ' ')
    text = re.sub(r' +', ' ', text).strip()
    return text, _warn(text)


def paragraphs(raw, corrections=None):
    text = _decode(raw)
    text = _BLOCK.sub('\n\n', text)
    text = _TAG.sub(' ', text)
    text = _apply_corrections(text, corrections)
    out, warnings = [], []
    for chunk in re.split(r'\n\s*\n+', text):
        chunk = re.sub(r'\s+', ' ', chunk).strip()
        if chunk:
            out.append(chunk)
            warnings.extend(_warn(chunk))
    return out, warnings


def unused_corrections(raw_texts, corrections):
    blob = ' '.join(_decode(t) for t in raw_texts)
    return [bad for bad in (corrections or {}) if bad not in blob]
