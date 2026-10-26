# Run: python -m pytest backend/tests (from the repo root, with aiohttp installed)
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from modules.providers.neocities import parse_sites  # noqa: E402

FIXTURES = pathlib.Path(__file__).parent / 'fixtures'


def test_reads_the_browse_page_markup_of_2026_10_25():
    # Neocities moved to background-image and multi-line titles; the old pattern found 0 sites and the backend gave 503
    sites = parse_sites((FIXTURES / 'browse-2026-10-25.html').read_text())
    assert len(sites) == 3
    for site in sites:
        assert site['url'].startswith('https://') and site['name'] and '\n' not in site['name']
        assert site['image'].startswith('https://neocities.org/site_screenshots/')


def test_still_reads_the_earlier_markup():
    old = ('<a href="https://example.neocities.org" class="neo-Screen-Shot" title="Example Site">'
           '<span class="img-Holder" style="background:url(/site_screenshots/1/2/example/index.html.540x405.webp)"></span></a>')
    assert parse_sites(old) == [{'name': 'Example Site', 'url': 'https://example.neocities.org',
                                 'image': 'https://neocities.org/site_screenshots/1/2/example/index.html.540x405.webp'}]
