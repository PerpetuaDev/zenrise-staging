# cms/tests/test_publish_gates.py
"""A tour publishes only when it is complete and bookable.

The earlier pipeline published an unpriced tour with an "in preparation"
layout, and published a tour whose Japanese slot held English. Both are now
held back: a tour on the site is one a visitor can actually read and book.

The recorded fixtures predate the client's Japanese work -- no product carries
an `en` version, and every Japanese slot holds English -- so a test that wants
a product to pass the gates says so explicitly with `complete()`.
"""
import unittest

from cms import bokun_source
from cms.tests.test_bokun_source import (
    CFG, DATA, FakeClient, IKEBANA, CANDLE, ZEN, SWORD, list_item)

JA_TITLE = '禅の旅'
JA_BODY = '<p>鎌倉の禅寺をめぐる、静かな半日の旅です。</p><p>坐禅と抹茶をご用意します。</p>'


def complete(*pids):
    """Overrides lifting a fixture product through the language gates."""
    ov = {}
    for pid in pids:
        ov[f'{pid}-EN'] = {'languages': ['en', 'JA_JP']}
        ov[f'{pid}-ja'] = {'title': JA_TITLE, 'description': JA_BODY}
    return ov


def run(pids, overrides=None, client=None):
    c = client or FakeClient(
        product_list=[{'id': 77, 'title': 'Website'}],
        product_list_items={77: [list_item(p) for p in pids]},
        overrides=overrides or {})
    return bokun_source.fetch_records(c, CFG)


def held(warnings):
    return [w for w in warnings if 'held back' in w]


NO_ENGLISH = {'languages': ['JA_JP']}
ENGLISH_IN_THE_JA_SLOT = {'description': '<p>A private candle-making session '
                                         'with a Shonan wax artist.</p>'}


class TestEnglishGate(unittest.TestCase):
    def test_a_product_with_no_english_version_is_held_back(self):
        # candle-making's real shape: languages is ['JA_JP'] only, which is
        # exactly why its English ended up in the Japanese slot.
        records, warnings = run([CANDLE], overrides={f'{CANDLE}-EN': NO_ENGLISH})
        self.assertEqual(records, [])
        self.assertTrue(any('English' in w for w in held(warnings)), warnings)

    def test_the_reason_names_the_product(self):
        _, warnings = run([CANDLE], overrides={f'{CANDLE}-EN': NO_ENGLISH})
        self.assertTrue(any(str(CANDLE) in w for w in held(warnings)), warnings)


class TestJapaneseGate(unittest.TestCase):
    def test_a_japanese_slot_holding_english_is_held_back(self):
        records, warnings = run(
            [IKEBANA], overrides={f'{IKEBANA}-ja': ENGLISH_IN_THE_JA_SLOT})
        self.assertEqual(records, [])
        self.assertTrue(any('Japanese' in w for w in held(warnings)), warnings)

    def test_real_japanese_passes(self):
        records, _ = run([ZEN], overrides=complete(ZEN))
        self.assertEqual([r['id'] for r in records], ['zen-journey'])


class TestBookableGate(unittest.TestCase):
    def test_a_product_with_no_availability_is_held_back(self):
        # Swordsmithing's real shape: 0 slots in the window.
        records, warnings = run([SWORD], overrides=complete(SWORD))
        self.assertEqual(records, [])
        self.assertTrue(any('bookable' in w or 'availability' in w
                            for w in held(warnings)), warnings)

    def test_an_unpriced_product_is_held_back(self):
        class Unpriced(FakeClient):
            def get(self, path):
                r = super().get(path)
                if '/availabilities' in path:
                    for slot in r:
                        slot['pricesByRate'] = []
                        slot['defaultPrice'] = 0
                return r
        c = Unpriced(product_list=[{'id': 77, 'title': 'Website'}],
                     product_list_items={77: [list_item(ZEN)]},
                     overrides=complete(ZEN))
        records, warnings = run(None, client=c)
        self.assertEqual(records, [])
        self.assertTrue(any('price' in w for w in held(warnings)), warnings)


class TestNoInPreparationLayout(unittest.TestCase):
    def test_every_published_tour_is_priced(self):
        records, _ = run([IKEBANA, CANDLE, ZEN, SWORD],
                         overrides=complete(IKEBANA, CANDLE, ZEN, SWORD))
        self.assertTrue(records)
        for r in records:
            self.assertTrue(r['priceEn'], f"{r['id']} published with no price")


if __name__ == '__main__':
    unittest.main()


class TestJapaneseIsTrusted(unittest.TestCase):
    """Tours are authored in Japanese, so the Japanese is the original.

    It used to be withheld behind a jaReviewed flag we set by hand, on the
    assumption that Bokun's Japanese was machine translation of an English
    original. That is the wrong way round: the client writes Japanese and
    translates outward, and the publish gates already refuse a tour whose
    Japanese slot holds English.
    """

    def test_japanese_renders_without_any_review_flag(self):
        entry = dict(CFG['tours'][str(ZEN)])
        entry.pop('jaReviewed', None)
        cfg = dict(CFG, tours=dict(CFG['tours'], **{str(ZEN): entry}))
        c = FakeClient(product_list=[{'id': 77, 'title': 'Website'}],
                       product_list_items={77: [list_item(ZEN)]},
                       overrides={f'{ZEN}-ja': {'title': JA_TITLE,
                                                'description': JA_BODY}})
        records, _ = bokun_source.fetch_records(c, cfg)
        self.assertEqual(records[0]['titleJa'], JA_TITLE)
        self.assertNotEqual(records[0]['titleJa'], records[0]['titleEn'])

    def test_the_review_flag_is_gone_from_the_record(self):
        records, _ = run([ZEN], overrides=complete(ZEN))
        self.assertNotIn('jaReviewed', records[0])


TERSE_JA = {'description': '<p>鎌倉の禅寺を歩く。</p>'}
KANJI_ONLY_JA = {'description': '<p>鎌倉五山禅寺巡礼半日</p>'}
MOSTLY_ENGLISH_JA = {'description': '<p>A walk through Kamakura 鎌倉, then Noge. '
                                    'Includes entrance fees and one drink.</p>'}


class TestUntranslatedJapanese(unittest.TestCase):
    """What actually needs catching is the untranslated case: Bokun serves the
    base text in the ja slot when nobody has written into it, so the two come
    back identical."""

    def test_a_japanese_slot_identical_to_the_english_is_held_back(self):
        # ikebana, candle-making and swordsmithing are all in this state:
        # Bokun returns the English text for the Japanese request.
        import json, os
        with open(os.path.join(DATA, f'activity-{ZEN}-EN.json')) as f:
            en_description = json.load(f)['description']
        records, warnings = run(
            [ZEN], overrides={f'{ZEN}-ja': {'description': en_description}})
        self.assertEqual(records, [])
        self.assertTrue(any('identical' in w for w in held(warnings)), warnings)

    def test_different_english_in_the_japanese_slot_is_held_back(self):
        records, warnings = run(
            [ZEN], overrides={f'{ZEN}-ja': ENGLISH_IN_THE_JA_SLOT})
        self.assertEqual(records, [])
        self.assertTrue(any('Japanese' in w for w in held(warnings)), warnings)


class TestNoFalseNegatives(unittest.TestCase):
    """Real Japanese publishes however terse or kanji-heavy it is."""

    def test_a_terse_japanese_description_publishes(self):
        records, _ = run([ZEN], overrides={f'{ZEN}-ja': TERSE_JA})
        self.assertEqual([r['id'] for r in records], ['zen-journey'])

    def test_a_kanji_only_japanese_description_publishes(self):
        records, _ = run([ZEN], overrides={f'{ZEN}-ja': KANJI_ONLY_JA})
        self.assertEqual([r['id'] for r in records], ['zen-journey'])

    def test_english_mixed_into_japanese_publishes(self):
        records, _ = run([ZEN], overrides={
            f'{ZEN}-ja': {'description': '<p>Zenrise の Ikebana Experience へ'
                                         'ようこそ。鎌倉の工房でお待ちしています。</p>'}})
        self.assertEqual([r['id'] for r in records], ['zen-journey'])


class TestMostlyEnglishWarns(unittest.TestCase):
    def test_a_mostly_english_japanese_field_publishes_but_warns(self):
        records, warnings = run([ZEN], overrides={f'{ZEN}-ja': MOSTLY_ENGLISH_JA})
        self.assertEqual([r['id'] for r in records], ['zen-journey'])
        self.assertTrue(any('mostly English' in w for w in warnings), warnings)
