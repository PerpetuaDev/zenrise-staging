"""Record real Bokun responses into cms/tests/data/ so tests run offline.

Run manually when the fixtures need refreshing:
    python3 cms/tests/record_fixtures.py
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from cms import bokun_client, tours_config  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def main():
    os.makedirs(DATA, exist_ok=True)
    client = bokun_client.from_env()
    cfg = tours_config.load()
    today = datetime.now(timezone.utc).date()
    end = today + timedelta(days=75)
    for pid in tours_config.catalogue_ids(cfg):
        for lang in ('EN', 'ja'):
            d = client.get(f'/activity.json/{pid}?lang={lang}')
            _write(f'activity-{pid}-{lang}.json', d)
        av = client.get(f'/activity.json/{pid}/availabilities?start={today}&end={end}')
        _write(f'availability-{pid}.json', av)
    print('recorded fixtures for', tours_config.catalogue_ids(cfg))


def _write(name, data):
    with open(os.path.join(DATA, name), 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
