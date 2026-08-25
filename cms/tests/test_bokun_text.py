import unittest
from cms import bokun_text

CORR = {'templ e grounds': 'temple grounds', 'wa l ked': 'walked'}


class TestClean(unittest.TestCase):
    def test_decodes_html_entities(self):
        text, _ = bokun_text.clean('Immerse yourself in &#34;Ichika Ichiei&#34;')
        self.assertEqual(text, 'Immerse yourself in "Ichika Ichiei"')

    def test_decodes_nbsp_as_a_plain_space(self):
        text, _ = bokun_text.clean('&nbsp;Meditation, gardens and matcha.')
        self.assertEqual(text, 'Meditation, gardens and matcha.')

    def test_strips_tags_and_collapses_whitespace(self):
        text, _ = bokun_text.clean('<p>Kamakura   has\n\nkept</p><p>its temples</p>')
        self.assertEqual(text, 'Kamakura has kept its temples')

    def test_applies_corrections(self):
        text, _ = bokun_text.clean('three templ e grounds wa l ked slowly', CORR)
        self.assertEqual(text, 'three temple grounds walked slowly')

    def test_corrections_apply_after_entity_decoding(self):
        text, _ = bokun_text.clean('&nbsp;templ e grounds', CORR)
        self.assertEqual(text, 'temple grounds')

    def test_warns_on_uncovered_damage(self):
        _, warnings = bokun_text.clean('a quiet passag e through', {})
        self.assertTrue(any('passag e through' in w for w in warnings))

    def test_no_warning_once_covered_by_corrections(self):
        _, warnings = bokun_text.clean('templ e grounds', CORR)
        self.assertEqual(warnings, [])

    def test_real_short_words_are_not_flagged_as_damage(self):
        for phrase in ['walk to Hase', 'one of three', 'tea is served',
                       'made by hand', 'sit in silence', 'up at dawn']:
            _, warnings = bokun_text.clean(phrase, {})
            self.assertEqual(warnings, [], f'false positive on {phrase!r}')

    def test_paragraphs_split_on_blank_lines(self):
        paras, _ = bokun_text.paragraphs('First para.\n\nSecond para.\n\n\nThird.')
        self.assertEqual(paras, ['First para.', 'Second para.', 'Third.'])

    def test_paragraphs_split_on_block_tags(self):
        paras, _ = bokun_text.paragraphs('<p>One.</p><p>Two.</p>')
        self.assertEqual(paras, ['One.', 'Two.'])

    def test_unused_corrections_reported(self):
        unused = bokun_text.unused_corrections(['temple grounds already fixed'], CORR)
        self.assertIn('templ e grounds', unused)
        self.assertIn('wa l ked', unused)

    def test_none_and_empty_are_safe(self):
        self.assertEqual(bokun_text.clean(None), ('', []))
        self.assertEqual(bokun_text.clean(''), ('', []))


if __name__ == '__main__':
    unittest.main()
