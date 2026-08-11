#!/usr/bin/env python3
"""Seed the microCMS `tours` API from cms/tours-fixture.json (one-time, after the
API is created from cms/tours-schema.json). PUTs each tour under its fixture id
so page filenames stay tour-<id>.html. Covers must be uploaded to microCMS media
and mapped afterwards — fixture cover paths are site-relative interim photos."""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
key = os.environ.get('MICROCMS_API_KEY')
if not key:
    for line in open(os.path.join(HERE, '.env')):
        if line.startswith('MICROCMS_API_KEY='):
            key = line.strip().split('=', 1)[1]

data = json.load(open(os.path.join(HERE, 'tours-fixture.json')))
ok = 0
for t in data['contents']:
    payload = {k: v for k, v in t.items() if k not in ('id', 'cover')}
    r = subprocess.run(['/usr/bin/curl', '-s', '-m', '30', '-X', 'PUT',
                        '-H', f'X-MICROCMS-API-KEY: {key}',
                        '-H', 'Content-Type: application/json',
                        '-d', json.dumps(payload, ensure_ascii=False),
                        f"https://zenrise.microcms.io/api/v1/tours/{t['id']}"],
                       capture_output=True, text=True)
    good = '"id"' in r.stdout
    ok += good
    print(t['id'], '->', 'OK' if good else r.stdout[:200])
print(f'{ok}/{len(data["contents"])} seeded')
sys.exit(0 if ok == len(data['contents']) else 1)
