import importlib.util, json, os, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_tours', os.path.join(ROOT, 'cms', 'build-tours.py'))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)

CH = 'e2350ad8-80af-4c18-a21a-acae6d72283f'


def _write_go_redirects_in_tmp(models, tmp):
    """Run write_go_redirects with bt.ROOT redirected to a scratch directory,
    so tests never write into this repo's real tree (which has no go/ at
    all -- see TestInstagramRedirectPreserved)."""
    old_root = bt.ROOT
    bt.ROOT = tmp
    try:
        return bt.write_go_redirects(models)
    finally:
        bt.ROOT = old_root


class TestRedirectHtml(unittest.TestCase):
    def test_redirects_to_the_widget_url(self):
        html = bt.go_redirect_html({'id': 's', 'full': True,
                                    'widgets': {'en': f'{CH}/experience-calendar/1'}})
        self.assertIn(f'https://widgets.bokun.io/online-sales/{CH}/experience-calendar/1', html)
        self.assertIn('http-equiv="refresh"', html)
        self.assertIn('location.replace', html)

    def test_is_noindex(self):
        html = bt.go_redirect_html({'id': 's', 'full': True, 'widgets': {'en': f'{CH}/x/1'}})
        self.assertIn('noindex', html)

    def test_no_page_without_a_widget(self):
        self.assertIsNone(bt.go_redirect_html({'id': 's', 'full': True, 'widgets': {}}))

    def test_no_page_for_an_unpriced_tour(self):
        self.assertIsNone(bt.go_redirect_html(
            {'id': 's', 'full': False, 'widgets': {'en': f'{CH}/x/1'}}))


class TestWriteGoRedirects(unittest.TestCase):
    """write_go_redirects must only ever create go/<slug>/ for configured,
    priced tours that carry a widget -- never an arbitrary or unexpected
    path -- and it must skip unpriced/un-widgeted tours entirely."""

    def test_writes_exactly_the_expected_slug_directories(self):
        models = [
            {'id': 'ikebana-ichigo-ichie', 'full': True, 'widgets': {'en': f'{CH}/a/1'}},
            {'id': 'candle-making', 'full': True, 'widgets': {'en': f'{CH}/b/1'}},
            {'id': 'zen-journey', 'full': False, 'widgets': {}},
            {'id': 'swordsmithing', 'full': False, 'widgets': {}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            written = _write_go_redirects_in_tmp(models, tmp)
            created = set(os.listdir(os.path.join(tmp, 'go')))

        self.assertEqual(set(written), {'go/ikebana-ichigo-ichie/', 'go/candle-making/'})
        self.assertEqual(created, {'ikebana-ichigo-ichie', 'candle-making'})


class TestInstagramRedirectPreserved(unittest.TestCase):
    def test_generated_slugs_cannot_collide_with_it(self):
        # go/kamakura/ is a live link from the Zenrise Instagram profile to an
        # OTA-tier tour (Bokun product 1272734) -- outside this work. This is
        # the property that actually protects it: as long as no configured
        # tour resolves to the slug "kamakura", write_go_redirects can never
        # produce a path that collides with it.
        with open(os.path.join(ROOT, 'cms', 'tours-config.json')) as f:
            cfg = json.load(f)
        self.assertNotIn('kamakura', {e['slug'] for e in cfg['tours'].values()})

    def test_build_never_writes_a_kamakura_redirect(self):
        # go/kamakura/ is production-only -- it does not exist in this
        # (staging) repo at all, the same way relay/ doesn't, and that's
        # correct: staging deliberately doesn't mirror it. But once this
        # build is ported to production, where the directory *does* exist,
        # write_go_redirects must never touch or regenerate it. Drive every
        # configured tour through write_go_redirects (as if each were priced
        # and widgeted) and confirm "kamakura" never appears among the paths
        # it reports writing -- tolerant of go/ not existing here at all.
        with open(os.path.join(ROOT, 'cms', 'tours-config.json')) as f:
            cfg = json.load(f)
        models = [{'id': e['slug'], 'full': True, 'widgets': {'en': f'{CH}/x/1'}}
                  for e in cfg['tours'].values()]

        with tempfile.TemporaryDirectory() as tmp:
            written = _write_go_redirects_in_tmp(models, tmp)

        self.assertNotIn('go/kamakura/', written)


if __name__ == '__main__':
    unittest.main()
