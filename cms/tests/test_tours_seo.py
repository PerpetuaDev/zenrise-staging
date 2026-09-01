import importlib.util, json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_tours', os.path.join(ROOT, 'cms', 'build-tours.py'))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)


def model(**over):
    m = {'id': 'ikebana-ichigo-ichie', 'K': 'tours_ikebana-ichigo-ichie', 'num': '01',
         'area': 'Kamakura', 'length': 'Half-day', 'themes': ['arts'],
         'cover': 'https://img/x.jpg', 'bokun_id': 1273232, 'widgets': {},
         'title': ('Ikebana', 'Ikebana'), 'sub': ('A private workshop.', ''),
         'lede': ('Ninety minutes with a master of the Sogetsu school.', ''),
         'hours': ('1 hour and 30 minutes', ''), 'coverCaption': ('', ''),
         'price_en': 'from ¥21,000 per adult', 'price_ja': '',
         'price_rows': [{'category': 'Adult', 'min': 3, 'max': 6,
                         'amount': 21000, 'currency': 'JPY'}],
         'route': []}
    m.update(over)
    return m


class TestJsonLd(unittest.TestCase):
    def test_emits_valid_json(self):
        raw = bt.json_ld(model())
        body = re.search(r'>(.*)</script>', raw, re.S).group(1)
        json.loads(body)

    def test_declares_a_product_with_an_offer(self):
        d = json.loads(re.search(r'>(.*)</script>', bt.json_ld(model()), re.S).group(1))
        self.assertEqual(d['@type'], 'Product')
        self.assertEqual(d['offers']['priceCurrency'], 'JPY')
        self.assertEqual(d['offers']['price'], 21000)

    def test_offer_asserts_no_availability_we_have_not_checked(self):
        d = json.loads(re.search(r'>(.*)</script>', bt.json_ld(model()), re.S).group(1))
        self.assertNotIn('availability', d['offers'])

    def test_unpriced_tour_emits_no_offer(self):
        d = json.loads(re.search(r'>(.*)</script>',
                                 bt.json_ld(model(price_rows=[])), re.S).group(1))
        self.assertNotIn('offers', d)

    def test_escapes_a_closing_script_tag_in_copy(self):
        raw = bt.json_ld(model(title=('</script><script>alert(1)</script>', '')))
        self.assertNotIn('</script><script>', raw)


class TestMetaDesc(unittest.TestCase):
    def test_prefers_the_sub(self):
        self.assertEqual(bt.meta_desc(model()), 'A private workshop.')

    def test_falls_back_to_the_lede_truncated_on_a_word_boundary(self):
        d = bt.meta_desc(model(sub=('', ''), lede=('word ' * 60, '')))
        self.assertLessEqual(len(d), 160)
        self.assertFalse(d.endswith('wor'))

    def test_never_empty(self):
        self.assertTrue(bt.meta_desc(model(sub=('', ''), lede=('', ''))))


class TestTemplatesAndSitemap(unittest.TestCase):
    def test_the_detail_template_carries_the_json_ld_slot(self):
        with open(os.path.join(ROOT, 'cms', 'templates', 'tour-detail.html')) as f:
            self.assertIn('{{JSON_LD}}', f.read())

    def test_sitemap_includes_tours_when_the_index_exists(self):
        news_spec = importlib.util.spec_from_file_location(
            'build_news', os.path.join(ROOT, 'cms', 'build-news.py'))
        bn = importlib.util.module_from_spec(news_spec)
        news_spec.loader.exec_module(bn)
        xml = bn.render_sitemap([])
        self.assertIn('https://zenrise.jp/tours.html', xml)
        # Every published tour, and only those: naming a slug here would make
        # the test fail whenever the client's catalogue changes.
        with open(os.path.join(ROOT, 'cms', 'tours-index.json')) as f:
            published = json.load(f)
        # Not assertTrue(published): an empty index is a legitimate state,
        # for the same reason a slug is not named above -- the catalogue is
        # the client's to change, and the gates can hold every tour back.
        for slug in published:
            self.assertIn(f'https://zenrise.jp/tour-{slug}.html', xml)


if __name__ == '__main__':
    unittest.main()
