#!/usr/bin/env python3
"""Staging-only build: real microCMS articles merged with cms/staging-samples.json.

The samples exist so the client can preview how CMS articles render before
authoring real ones. To retire them, delete this file and staging-samples.json
and point .github/workflows/build-news.yml back at build-news.py.
"""
import importlib.util, json, os

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('build_news', os.path.join(here, 'build-news.py'))
bn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bn)

fetch_real = bn.fetch_articles


def fetch_with_samples():
    articles = fetch_real() + json.load(open(os.path.join(here, 'staging-samples.json')))
    articles.sort(key=lambda a: a['date'], reverse=True)
    return articles


bn.fetch_articles = fetch_with_samples
bn.main()
