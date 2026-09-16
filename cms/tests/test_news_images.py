# cms/tests/test_news_images.py
import glob
import importlib.util
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    'build_news', os.path.join(ROOT, 'cms', 'build-news.py'))
bn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bn)

TRANSFORMS = ('IMG_PAGE', 'IMG_FIG', 'IMG_FIG_TALL', 'IMG_CARD', 'IMG_OG')
# Any occurrence, not just the CSS url('...') form: og:image and
# twitter:image are built from IMG_OG and sit in <meta content="...">, so a
# regression confined to the link-preview frame used to pass unnoticed.
CMS_IMG = re.compile(r"https://images\.microcms-assets\.io/[^\"'\s>]+")


class TestTransforms(unittest.TestCase):
    """Asking microCMS for a width alone leaves the aspect ratio to chance:
    the rendition arrives in the source's own shape and the fixed-height CSS
    slot centre-crops whatever it gets. A 2334x3500 portrait hero was sliced
    through the hand that way (2026-09-16)."""

    def test_every_transform_pins_both_dimensions(self):
        for name in TRANSFORMS:
            value = getattr(bn, name)
            self.assertRegex(value, r'[?&]w=\d+', name)
            self.assertRegex(value, r'[?&]h=\d+', name)

    def test_every_transform_crops_rather_than_squashing(self):
        for name in TRANSFORMS:
            self.assertIn('fit=crop', getattr(bn, name), name)

    def test_every_transform_picks_the_crop_by_content(self):
        # center slices whatever sits at the frame edge; entropy keeps the
        # subject whole and lets the cut fall on empty ground.
        for name in TRANSFORMS:
            self.assertIn('crop=', getattr(bn, name), name)


def ratio(transform):
    """w/h out of a transform query string."""
    w = int(re.search(r'[?&]w=(\d+)', transform).group(1))
    h = int(re.search(r'[?&]h=(\d+)', transform).group(1))
    return w / h


class TestTallSlot(unittest.TestCase):
    """A portrait figure is routed to `.fig .ph.tall`, which is 880x720 on
    desktop (1.22) and about 1.11 on mobile. Feeding it the same 16:9
    rendition as the default slot cuts the portrait to a landscape band
    first, then the box crops that band's sides -- strictly worse than the
    slot it was promoted out of."""

    def test_the_tall_slot_asks_for_a_taller_frame_than_the_default(self):
        self.assertLess(ratio(bn.IMG_FIG_TALL), ratio(bn.IMG_FIG))

    def test_the_tall_frame_roughly_matches_its_box(self):
        # box is 1.22 desktop / ~1.11 mobile; anything landscape defeats it
        self.assertLess(ratio(bn.IMG_FIG_TALL), 1.4)


class TestBuiltPages(unittest.TestCase):
    """The invariant on the real pages: no CMS image is ever requested in an
    unconstrained shape."""

    @classmethod
    def setUpClass(cls):
        cls.pages = {}
        for p in glob.glob(os.path.join(ROOT, 'news*.html')):
            with open(p, encoding='utf-8') as f:
                cls.pages[os.path.basename(p)] = f.read()

    def test_there_are_pages_to_check(self):
        self.assertTrue(self.pages)

    def test_tall_figures_are_requested_in_a_tall_frame(self):
        fig = re.compile(
            r"""<div class="ph( tall)?" style="background-image: url\('([^']+)'\)""")
        seen = 0
        for name, html in self.pages.items():
            for tall, url in fig.findall(html):
                if 'images.microcms-assets.io' not in url:
                    continue
                seen += 1
                r = ratio(url.replace('&amp;', '&'))
                if tall:
                    self.assertLess(r, 1.4, f'{name}: tall figure got {r:.2f}')
                else:
                    self.assertGreater(r, 1.4, f'{name}: wide figure got {r:.2f}')
        self.assertTrue(seen, 'no CMS figures found to check')

    def test_no_cms_image_is_requested_without_a_crop(self):
        bad = []
        for name, html in self.pages.items():
            for url in CMS_IMG.findall(html):
                if 'fit=crop' not in url:
                    bad.append(f'{name}: {url}')
        self.assertEqual(bad, [])


if __name__ == '__main__':
    unittest.main()
