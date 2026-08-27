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
    # honorifics: "with Mr Tanaka" is a two-letter token between two words and
    # otherwise reads as spacing damage. Deliberately not 'st' -- that would
    # mask real damage such as "fir st class".
    'mr', 'ms', 'dr',
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
    # A newline, not a space: _strip_pdf() below works per line, so substituting
    # a space here would hide the "PDF" debris at an HTML block boundary and
    # strip it only where the source happened to carry a literal newline. The
    # newlines collapse back to spaces at the end of this function, so
    # single-line output is unchanged.
    text = _BLOCK.sub('\n', text)
    text = _TAG.sub(' ', text)
    text = _apply_corrections(text, corrections)
    text = '\n'.join(_strip_pdf(l) for l in text.split('\n'))
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


# Copy pasted into Bokun left a literal "PDF" at the end of every list item and
# on its own between blocks. It is debris, not content, so it is removed at a
# line boundary only -- never mid-sentence, where PDF may be a real word.
_PDF_LINE = re.compile(r'^\s*PDF\s*$')
_PDF_TAIL = re.compile(r'PDF\s*$')

_INCLUDED_HEADINGS = ('what is included', "what's included", 'inclusions')
_HEADING = re.compile(r'^(.{2,60}?):\s*$')

# Bokun's included/excluded/requirements/attention fields are rich text
# shaped <div><p><strong>heading</strong></p><ul><li>item</li>...</ul></div>.
# The heading is discarded (task 17: our own group labels are used instead);
# only the ordered <li> contents matter.
_LIST_ITEM = re.compile(r'(?is)<li\b[^>]*>(.*?)</li>')


def list_items(raw):
    """Ordered, uncleaned inner-HTML of each <li> in a Bokun rich-text field.

    Each item is returned with entities, inline tags/styles, and \\r\\n still
    intact, so a caller can run it through the same clean()/corrections path
    as any other Bokun text rather than a second, divergent one."""
    if not raw:
        return []
    return [m.group(1) for m in _LIST_ITEM.finditer(raw)]


def _strip_pdf(line):
    return _PDF_TAIL.sub('', line).strip()


def _lines(raw):
    text = _decode(raw)
    text = _BLOCK.sub('\n', text)
    text = _TAG.sub(' ', text)
    out = []
    for line in text.split('\n'):
        line = re.sub(r'\s+', ' ', line).strip()
        if not line or _PDF_LINE.match(line):
            continue
        out.append(_strip_pdf(line))
    return [l for l in out if l]


def sections(raw, corrections=None, chips_heading=None):
    """Split a Bokun description into a lede and its named sections.

    Bokun has no inclusions field, but some products carry the list inline under
    a heading. See spec section 3.4.1.
    """
    wanted = [chips_heading.strip().lower()] if chips_heading else list(_INCLUDED_HEADINGS)
    lede, included, warnings = [], [], []
    current = None
    for line in _lines(raw):
        line = _apply_corrections(line, corrections)
        heading = _HEADING.match(line)
        if heading:
            current = heading.group(1).strip().lower()
            continue
        if current is None:
            lede.append(line)
            warnings.extend(_warn(line))
        elif current in wanted:
            included.append(line)
            warnings.extend(_warn(line))
        # Any other section (itinerary, practical notes) is dropped: agendaItems
        # already carries the itinerary, and prose notes are not chips.
    return {'lede': lede, 'included': included}, warnings
