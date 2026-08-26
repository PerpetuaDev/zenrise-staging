# cms/tests/test_no_orphans.py
import glob, json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(p):
    with open(os.path.join(ROOT, p)) as f:
        return f.read()


class TestNoOrphans(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, 'cms', 'tours-config.json')) as f:
            cfg = json.load(f)
        self.slugs = {entry['slug'] for entry in cfg['tours'].values()}

    def test_only_generated_tour_pages_exist(self):
        on_disk = {os.path.basename(p)[len('tour-'):-len('.html')]
                   for p in glob.glob(os.path.join(ROOT, 'tour-*.html'))}
        self.assertEqual(on_disk, self.slugs)

    def test_retired_fixtures_and_schemas_are_gone(self):
        for p in ('cms/tours-fixture.json', 'cms/tours-schema.json',
                  'cms/site-config-schema.json', 'cms/push-tours.py',
                  'cms/tour-routes.json'):
            self.assertFalse(os.path.exists(os.path.join(ROOT, p)), p)

    def test_no_link_points_at_a_retired_tour_page(self):
        retired = ['kita-kamakura-hase', 'tsurugaoka', 'enoshima',
                   'farmers-market', 'zen-morning', 'yokohama']
        for page in glob.glob(os.path.join(ROOT, '*.html')):
            if 'archive' in page:
                continue
            body = read(os.path.basename(page))
            for slug in retired:
                self.assertNotIn(f'tour-{slug}.html', body,
                                 f'{os.path.basename(page)} links to retired tour-{slug}.html')

    def test_superseded_draft_lang_keys_are_gone(self):
        lang = read('lang.js')
        for key in ('tours_c1_', 'tours_d1_', 'rt04_'):
            self.assertNotIn(key, lang, key)

    def test_keys_orphaned_by_the_calendar_removal_are_gone(self):
        # These labelled the hand-built calendar that Task 8 replaced with the
        # Bokun widget. Nothing references them any more.
        lang = read('lang.js')
        for key in ('td_book_label', 'td_cal_note', 'td_travellers',
                    'td_choose', 'td_request'):
            self.assertNotIn(key, lang, key)

    def test_archive_is_untouched(self):
        self.assertTrue(os.path.exists(os.path.join(ROOT, 'archive/custom-booking/index.html')))
        self.assertIn("var RELAY_URL = ''", read('archive/custom-booking/index.html'))


if __name__ == '__main__':
    unittest.main()
