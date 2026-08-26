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


IKEBANA_DESC = (
    'Experience the Art of Ikebana in Kamakura with Master Koen Yokoi\n'
    'Immerse yourself in &#34;Ichika Ichiei&#34; a 90-minute private workshop.\n'
    'PDF\n'
    'Tour Highlights &amp; Itinerary (90 minutes):\n'
    'History &amp; Philosophy (30 mins): Learn about the heritage.PDF\n'
    'Tea &amp; Conversation (30 mins): Relax and reflect.PDF\n'
    'What is Included:\n'
    'PDF\n'
    'Private Ikebana instruction by Master Koen YokoiPDF\n'
    'All flower materials, tools, and equipmentPDF\n'
    'Tour insurancePDF\n')


class TestPdfArtifact(unittest.TestCase):
    def test_strips_standalone_pdf_lines(self):
        text, _ = bokun_text.clean('One.\nPDF\nTwo.')
        self.assertNotIn('PDF', text)

    def test_strips_trailing_pdf_tokens(self):
        text, _ = bokun_text.clean('Tour insurancePDF')
        self.assertEqual(text, 'Tour insurance')

    def test_keeps_pdf_used_as_a_real_word(self):
        text, _ = bokun_text.clean('Download the PDF guide before arriving.')
        self.assertIn('PDF guide', text)


class TestSections(unittest.TestCase):
    def setUp(self):
        self.parsed, self.warnings = bokun_text.sections(IKEBANA_DESC)

    def test_lede_is_everything_before_the_first_heading(self):
        self.assertEqual(len(self.parsed['lede']), 2)
        self.assertIn('Master Koen Yokoi', self.parsed['lede'][0])
        self.assertNotIn('What is Included', ' '.join(self.parsed['lede']))

    def test_inclusions_extracted_from_the_included_heading(self):
        self.assertEqual(self.parsed['included'], [
            'Private Ikebana instruction by Master Koen Yokoi',
            'All flower materials, tools, and equipment',
            'Tour insurance'])

    def test_itinerary_heading_is_ignored_agenda_items_own_that(self):
        self.assertNotIn('History & Philosophy (30 mins): Learn about the heritage.',
                         self.parsed['included'])

    def test_entities_are_decoded_in_sections(self):
        self.assertNotIn('&#34;', ' '.join(self.parsed['lede']))

    def test_unstructured_description_is_all_lede_and_no_chips(self):
        parsed, _ = bokun_text.sections(
            'Zenrise designs slow, considered private experiences around Kamakura.')
        self.assertEqual(len(parsed['lede']), 1)
        self.assertEqual(parsed['included'], [])

    def test_prose_inclusions_are_not_parsed_into_chips(self):
        # The Zen Journey states inclusions as a sentence under a different
        # heading; that must not become chips.
        parsed, _ = bokun_text.sections(
            'A slow pass through three temples.\n'
            'Practical Notes\n'
            'The tour is all-inclusive: transport, admission, lunch.')
        self.assertEqual(parsed['included'], [])

    def test_custom_heading_override_is_honoured(self):
        parsed, _ = bokun_text.sections(
            'Lede.\nInclusions:\nGuide\nTea', chips_heading='Inclusions')
        self.assertEqual(parsed['included'], ['Guide', 'Tea'])


# Bokun's included/excluded/requirements/attention fields, shaped as verified
# live on product 1273194 (task 17).
RICH_LIST_FIELD = (
    '<div>\r\n <p style="font-size:14px;color:#57646f">'
    '<strong>What\'s included in the tour</strong></p>\r\n '
    '<ul><li style="font-size:14px;color:#57646f">A dedicated guide will '
    'accompany you throughout</li><li style="font-size:14px;color:#57646f">'
    'Admission fees to <strong>Meigetsu-in</strong> Temple</li></ul></div>')


class TestListItems(unittest.TestCase):
    def test_extracts_li_contents_in_order(self):
        self.assertEqual(bokun_text.list_items(RICH_LIST_FIELD), [
            'A dedicated guide will accompany you throughout',
            'Admission fees to <strong>Meigetsu-in</strong> Temple'])

    def test_discards_the_heading_paragraph(self):
        for item in bokun_text.list_items(RICH_LIST_FIELD):
            self.assertNotIn("What's included", item)

    def test_none_and_no_list_are_safe(self):
        self.assertEqual(bokun_text.list_items(None), [])
        self.assertEqual(bokun_text.list_items(''), [])
        self.assertEqual(bokun_text.list_items('<div><p>Just a sentence.</p></div>'), [])

    def test_items_still_need_clean_to_strip_nested_tags_and_entities(self):
        # list_items() deliberately returns uncleaned items -- clean() (or a
        # caller's cl()) is responsible for entities/tags/corrections, same
        # as every other Bokun text path.
        item = bokun_text.list_items(RICH_LIST_FIELD)[1]
        self.assertIn('<strong>', item)
        text, _ = bokun_text.clean(item)
        self.assertEqual(text, 'Admission fees to Meigetsu-in Temple')


if __name__ == '__main__':
    unittest.main()
