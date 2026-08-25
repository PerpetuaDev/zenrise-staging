import json, os, tempfile, unittest
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


if __name__ == '__main__':
    unittest.main()
