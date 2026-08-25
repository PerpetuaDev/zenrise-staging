import json, os, tempfile, unittest
from cms import tours_config


def write(tmp, data):
    p = os.path.join(tmp, 'c.json')
    with open(p, 'w') as f:
        json.dump(data, f)
    return p


class TestLoad(unittest.TestCase):
    def test_catalogue_ids_returns_allowlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tours_config.load(write(tmp, {'allowlist': [1273232, 1273235], 'tours': {}}))
            self.assertEqual(tours_config.catalogue_ids(cfg), [1273232, 1273235])

    def test_empty_allowlist_is_an_error_not_a_wildcard(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tours_config.load(write(tmp, {'allowlist': [], 'tours': {}}))
            with self.assertRaises(tours_config.ConfigError):
                tours_config.catalogue_ids(cfg)

    def test_tour_entry_found_by_int_or_str_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tours_config.load(write(tmp, {
                'allowlist': [1273232],
                'tours': {'1273232': {'slug': 'ikebana-ichigo-ichie', 'number': '01'}}}))
            self.assertEqual(tours_config.tour_entry(cfg, 1273232)['slug'], 'ikebana-ichigo-ichie')

    def test_missing_tour_entry_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tours_config.load(write(tmp, {'allowlist': [999], 'tours': {}}))
            with self.assertRaises(tours_config.ConfigError):
                tours_config.tour_entry(cfg, 999)

    def test_entry_without_slug_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tours_config.load(write(tmp, {'allowlist': [1], 'tours': {'1': {'number': '01'}}}))
            with self.assertRaises(tours_config.ConfigError):
                tours_config.tour_entry(cfg, 1)

    def test_corrections_defaults_to_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tours_config.load(write(tmp, {'allowlist': [1], 'tours': {}}))
            self.assertEqual(tours_config.corrections(cfg), {})


if __name__ == '__main__':
    unittest.main()
