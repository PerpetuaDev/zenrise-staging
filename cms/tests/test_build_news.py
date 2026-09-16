# cms/tests/test_build_news.py
import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_news', os.path.join(ROOT, 'cms', 'build-news.py'))
bn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bn)


def pages(total, per_page=100):
    """A fake microCMS that pages exactly as the real one does."""
    items = [{'id': f'a{i}'} for i in range(total)]

    def transport(url, headers):
        offset = 0
        for part in url.split('?', 1)[1].split('&'):
            if part.startswith('offset='):
                offset = int(part.split('=', 1)[1])
        return {'totalCount': total, 'contents': items[offset:offset + per_page]}

    return transport


class TestPagination(unittest.TestCase):
    """The stale sweep deletes any news-*.html the fetch did not return, so an
    article that falls off the end of the response loses its published page."""

    def test_a_single_page_is_returned_whole(self):
        got = bn.fetch_articles(transport=pages(6), service='s', key='k')
        self.assertEqual(len(got), 6)

    def test_more_articles_than_one_page_are_all_fetched(self):
        got = bn.fetch_articles(transport=pages(150), service='s', key='k')
        self.assertEqual(len(got), 150)
        self.assertEqual(got[-1]['id'], 'a149')

    def test_an_exact_multiple_of_the_page_size_does_not_loop(self):
        got = bn.fetch_articles(transport=pages(200), service='s', key='k')
        self.assertEqual(len(got), 200)

    def test_a_response_without_a_total_is_taken_as_complete(self):
        def transport(url, headers):
            return {'contents': [{'id': 'only'}]}
        self.assertEqual(len(bn.fetch_articles(transport=transport,
                                               service='s', key='k')), 1)


class TestEmptyGuard(unittest.TestCase):
    """A 200 carrying an empty contents list is indistinguishable from a real
    build, and the stale sweep would then delete every article page. Before the
    hourly schedule that could only happen while a human watched; now it cannot
    be allowed to happen unattended."""

    def test_an_empty_catalogue_is_refused(self):
        with self.assertRaises(bn.BuildError):
            bn.check_not_empty([])

    def test_an_empty_catalogue_is_allowed_when_asked_for_explicitly(self):
        bn.check_not_empty([], allow_empty=True)   # must not raise

    def test_a_normal_catalogue_passes(self):
        bn.check_not_empty([{'id': 'a'}])


if __name__ == '__main__':
    unittest.main()
