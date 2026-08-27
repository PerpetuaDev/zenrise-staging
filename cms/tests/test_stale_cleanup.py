import importlib.util, io, os, tempfile, unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_tours', os.path.join(ROOT, 'cms', 'build-tours.py'))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)


def _touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write('x')


def _write_page_and_redirect(root, slug):
    _touch(os.path.join(root, f'tour-{slug}.html'))
    _touch(os.path.join(root, 'go', slug, 'index.html'))


class TestCleanupStalePages(unittest.TestCase):
    """cleanup_stale_pages() removes tour-<slug>.html and go/<slug>/ for a
    slug that is frozen in the registry but absent from this build's
    resolved catalogue -- see the task-3-4 brief's stale-page-cleanup
    section. tours_slug.load_registry is mocked throughout so these tests
    never touch the real, committed cms/tours-slugs.json."""

    def test_removes_a_slug_that_dropped_out_of_the_catalogue(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_page_and_redirect(tmp, 'a')
            _write_page_and_redirect(tmp, 'b')
            models = [{'id': 'a'}]  # 'b' is frozen but no longer catalogued
            with mock.patch('cms.tours_slug.load_registry',
                            return_value={'1': 'a', '2': 'b'}):
                removed = bt.cleanup_stale_pages(models, root=tmp)

            self.assertEqual(set(removed), {'tour-b.html', 'go/b/'})
            self.assertTrue(os.path.exists(os.path.join(tmp, 'tour-a.html')))
            self.assertTrue(os.path.exists(os.path.join(tmp, 'go', 'a')))
            self.assertFalse(os.path.exists(os.path.join(tmp, 'tour-b.html')))
            self.assertFalse(os.path.exists(os.path.join(tmp, 'go', 'b')))

    def test_nothing_removed_when_every_registered_slug_is_still_catalogued(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_page_and_redirect(tmp, 'a')
            models = [{'id': 'a'}]
            with mock.patch('cms.tours_slug.load_registry', return_value={'1': 'a'}):
                removed = bt.cleanup_stale_pages(models, root=tmp)
            self.assertEqual(removed, [])
            self.assertTrue(os.path.exists(os.path.join(tmp, 'tour-a.html')))

    def test_never_touches_kamakura_even_if_it_somehow_matched(self):
        # go/kamakura/ is a live Instagram link to an OTA tour, entirely
        # outside this system -- guarded by name as a hard rule, independent
        # of whatever the registry says.
        with tempfile.TemporaryDirectory() as tmp:
            _touch(os.path.join(tmp, 'go', 'kamakura', 'index.html'))
            models = []
            with mock.patch('cms.tours_slug.load_registry',
                            return_value={'1272734': 'kamakura'}):
                removed = bt.cleanup_stale_pages(models, root=tmp)
            self.assertEqual(removed, [])
            self.assertTrue(os.path.exists(os.path.join(tmp, 'go', 'kamakura', 'index.html')))

    def test_an_unaccounted_page_is_warned_about_and_left_alone(self):
        # In neither the resolved catalogue nor the slug registry: this must
        # never be guessed about and deleted.
        with tempfile.TemporaryDirectory() as tmp:
            _touch(os.path.join(tmp, 'tour-a.html'))
            _touch(os.path.join(tmp, 'tour-mystery.html'))
            models = [{'id': 'a'}]
            with mock.patch('cms.tours_slug.load_registry', return_value={'1': 'a'}):
                out = io.StringIO()
                with redirect_stdout(out):
                    removed = bt.cleanup_stale_pages(models, root=tmp)
            self.assertEqual(removed, [])
            self.assertTrue(os.path.exists(os.path.join(tmp, 'tour-mystery.html')))
            self.assertIn('tour-mystery.html', out.getvalue())
            self.assertIn('WARNING', out.getvalue())

    def test_a_sample_tour_slug_is_never_touched(self):
        # Sample tours (staging only) carry no Bokun product and are never in
        # the slug registry -- they must not be treated as unaccounted-for
        # just because their slug isn't a registry key.
        with tempfile.TemporaryDirectory() as tmp:
            _touch(os.path.join(tmp, 'tour-yokohama-harbour-evening.html'))
            models = [{'id': 'yokohama-harbour-evening'}]
            with mock.patch('cms.tours_slug.load_registry', return_value={}):
                out = io.StringIO()
                with redirect_stdout(out):
                    removed = bt.cleanup_stale_pages(models, root=tmp)
            self.assertEqual(removed, [])
            self.assertNotIn('yokohama-harbour-evening', out.getvalue())
            self.assertTrue(os.path.exists(
                os.path.join(tmp, 'tour-yokohama-harbour-evening.html')))

    def test_missing_page_or_redirect_is_tolerated(self):
        # A slug can be frozen but only ever have had a page, or only ever a
        # redirect (e.g. never priced/widgeted) -- removal must not choke on
        # a half-existing pair.
        with tempfile.TemporaryDirectory() as tmp:
            _touch(os.path.join(tmp, 'tour-b.html'))  # no go/b/ at all
            models = []
            with mock.patch('cms.tours_slug.load_registry', return_value={'1': 'b'}):
                removed = bt.cleanup_stale_pages(models, root=tmp)
            self.assertEqual(removed, ['tour-b.html'])


if __name__ == '__main__':
    unittest.main()
