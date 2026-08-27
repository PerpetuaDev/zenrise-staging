import json, os, tempfile, unittest
from unittest import mock
from cms import tours_build_source as tbs


class TestCache(unittest.TestCase):
    def test_writes_then_reads_the_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'cache.json')
            tbs.write_cache(p, [{'id': 'ikebana-ichigo-ichie'}])
            self.assertEqual(tbs.read_cache(p), [{'id': 'ikebana-ichigo-ichie'}])

    def test_missing_cache_reads_as_none(self):
        self.assertIsNone(tbs.read_cache('/nonexistent/cache.json'))

    def test_bokun_failure_falls_back_to_cache_with_a_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'cache.json')
            tbs.write_cache(p, [{'id': 'cached'}])

            def boom(client, cfg):
                raise RuntimeError('bokun down')

            recs, warnings = tbs.records_with_fallback(
                fetch=boom, client=None, cfg={}, cache_path=p)
            self.assertEqual(recs, [{'id': 'cached'}])
            self.assertTrue(any('cache' in w for w in warnings))

    def test_bokun_failure_with_no_cache_raises(self):
        def boom(client, cfg):
            raise RuntimeError('bokun down')

        with self.assertRaises(RuntimeError):
            tbs.records_with_fallback(fetch=boom, client=None, cfg={},
                                     cache_path='/nonexistent/c.json')

    def test_success_refreshes_the_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'cache.json')

            def ok(client, cfg):
                return [{'id': 'fresh'}], []

            recs, _ = tbs.records_with_fallback(fetch=ok, client=None, cfg={}, cache_path=p)
            self.assertEqual(recs, [{'id': 'fresh'}])
            self.assertEqual(tbs.read_cache(p), [{'id': 'fresh'}])


class TestLoadRecordsSourceSelection(unittest.TestCase):
    """load_records's source dispatch. None of these perform a live fetch:
    the 'bokun' path is exercised elsewhere (build-tours.py's own live run),
    not here."""

    def test_cache_source_does_not_construct_a_bokun_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'cache.json')
            tbs.write_cache(p, [{'id': 'cached'}])
            # If load_records touched the network layer for source='cache',
            # this would raise instead of returning the cached records --
            # proving a cache build needs no Bokun credentials at all.
            with mock.patch('cms.bokun_client.from_env',
                             side_effect=AssertionError(
                                 'should not construct a Bokun client for source=cache')):
                recs, cfg, warnings = tbs.load_records(source='cache', cache_path=p)
            self.assertEqual(recs, [{'id': 'cached'}])

    def test_cache_source_with_no_cache_raises(self):
        with self.assertRaises(RuntimeError):
            tbs.load_records(source='cache', cache_path='/nonexistent/c.json')

    def test_unknown_source_raises_value_error_naming_it(self):
        with self.assertRaises(ValueError) as ctx:
            tbs.load_records(source='fixture', cache_path='/nonexistent/c.json')
        self.assertIn('fixture', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()


class TestRequireLive(unittest.TestCase):
    """An unattended build must fail rather than quietly use the cache.

    A silent fallback produces no diff, so a scheduled job with bad credentials
    would report "no changes to publish" forever and look healthy.
    """

    def boom(self, client, cfg):
        raise RuntimeError('credentials rejected')

    def test_fallback_is_used_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'cache.json')
            tbs.write_cache(p, [{'id': 'a'}])
            recs, warns = tbs.records_with_fallback(self.boom, None, {}, p)
            self.assertEqual(recs, [{'id': 'a'}])
            self.assertTrue(any('fetch failed' in w for w in warns))

    def test_require_live_raises_even_with_a_usable_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'cache.json')
            tbs.write_cache(p, [{'id': 'a'}])
            with self.assertRaises(RuntimeError):
                tbs.records_with_fallback(self.boom, None, {}, p, require_live=True)

    def test_load_records_passes_the_flag_through(self):
        import inspect
        self.assertIn('require_live',
                      inspect.signature(tbs.load_records).parameters)
