import base64, hashlib, hmac, json, os, tempfile, unittest
from cms import bokun_client


class TestSign(unittest.TestCase):
    def test_signature_matches_the_documented_scheme(self):
        got = bokun_client.sign('sec', '2026-08-25 10:00:00', 'AK', 'GET', '/x.json/1')
        want = base64.b64encode(hmac.new(
            b'sec', b'2026-08-25 10:00:00AKGET/x.json/1', hashlib.sha1).digest()).decode()
        self.assertEqual(got, want)


class TestCredentials(unittest.TestCase):
    def test_reads_keys_and_ignores_comments_and_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'env')
            with open(p, 'w') as f:
                f.write('# comment\nBOKUN_ACCESS_KEY="ak"\nBOKUN_SECRET_KEY=sk\n\n')
            self.assertEqual(bokun_client.load_credentials(p), ('ak', 'sk'))

    def test_missing_key_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'env')
            with open(p, 'w') as f:
                f.write('BOKUN_ACCESS_KEY=ak\n')
            with self.assertRaises(bokun_client.BokunError):
                bokun_client.load_credentials(p)


class FakeTransport:
    def __init__(self, status=200, payload=b'{"ok":true}'):
        self.status, self.payload, self.calls = status, payload, []

    def __call__(self, method, url, headers, body):
        self.calls.append({'method': method, 'url': url, 'headers': headers, 'body': body})
        return self.status, self.payload


class TestClient(unittest.TestCase):
    def test_get_sends_the_three_auth_headers(self):
        t = FakeTransport()
        bokun_client.BokunClient('AK', 'sec', transport=t).get('/activity.json/1')
        h = t.calls[0]['headers']
        self.assertEqual(h['X-Bokun-AccessKey'], 'AK')
        self.assertIn('X-Bokun-Date', h)
        self.assertIn('X-Bokun-Signature', h)
        self.assertEqual(t.calls[0]['url'], 'https://api.bokun.io/activity.json/1')

    def test_signature_covers_the_path_including_query(self):
        t = FakeTransport()
        c = bokun_client.BokunClient('AK', 'sec', transport=t)
        c.get('/activity.json/1?lang=EN')
        date = t.calls[0]['headers']['X-Bokun-Date']
        self.assertEqual(t.calls[0]['headers']['X-Bokun-Signature'],
                         bokun_client.sign('sec', date, 'AK', 'GET', '/activity.json/1?lang=EN'))

    def test_post_sends_json_body_and_parses_response(self):
        t = FakeTransport(payload=b'{"totalHits":11}')
        c = bokun_client.BokunClient('AK', 'sec', transport=t)
        self.assertEqual(c.post('/activity.json/search', {'page': 1}), {'totalHits': 11})
        self.assertEqual(json.loads(t.calls[0]['body']), {'page': 1})
        self.assertEqual(t.calls[0]['method'], 'POST')

    def test_non_2xx_raises_with_the_path(self):
        c = bokun_client.BokunClient('AK', 'sec', transport=FakeTransport(status=404, payload=b'nope'))
        with self.assertRaises(bokun_client.BokunError) as ctx:
            c.get('/missing.json')
        self.assertIn('/missing.json', str(ctx.exception))

    def test_credentials_never_appear_in_the_error(self):
        c = bokun_client.BokunClient('AKSECRETVALUE', 'sec', transport=FakeTransport(status=500))
        with self.assertRaises(bokun_client.BokunError) as ctx:
            c.get('/x')
        self.assertNotIn('AKSECRETVALUE', str(ctx.exception))
        self.assertNotIn('sec', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
