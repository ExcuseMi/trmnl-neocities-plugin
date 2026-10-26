# Run: python3 -m pytest plugin/test
import io
import pathlib
import socket
import sys
import urllib.error

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'src'))
import transform  # noqa: E402

PAGE = (pathlib.Path(__file__).parent / 'browse-2026-10-25.html').read_bytes()  # a cut of the live page: 3 sites


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Asked(list):
    """The requests made; answers: what the next requests get (the page by default)"""
    answers = None


@pytest.fixture
def neocities(monkeypatch):
    asked = Asked()
    asked.answers = []

    def urlopen(request, timeout=None):
        asked.append((request.full_url, timeout, request.headers))
        answer = asked.answers.pop(0) if asked.answers else PAGE
        if isinstance(answer, Exception):
            raise answer
        return Response(answer)
    monkeypatch.setattr(transform.urllib.request, 'urlopen', urlopen)
    return asked


def run(values=None, previous=None):
    return transform.run({'trmnl': {'plugin_settings': {'custom_fields_values': values or {}},
                                    'previous_merge_variables': previous or {}}})


def test_four_sites_at_most_with_name_url_and_screenshot(neocities):
    items = run({'sort_by': 'random'})['items']
    assert len(items) == 3  # the fixture page holds three
    for site in items:
        assert site['url'].startswith('https://') and site['name'] and '\n' not in site['name']
        assert site['image'].startswith('https://neocities.org/site_screenshots/')
    url, timeout, _ = neocities[0]
    assert 'sort_by=random' in url and timeout <= transform.TIMEOUT_SECONDS
    assert len(neocities) == 1  # one request per refresh


def test_unknown_sort_falls_back_and_pages_vary(neocities):
    for _ in range(30):
        run({'sort_by': 'nonsense'})
    pages = {url.rsplit('page=', 1)[1] for url, _, _ in neocities}
    assert all('sort_by=special_sauce' in url for url, _, _ in neocities) and pages <= {'1', '2', '3', '4', '5'}
    assert len(pages) > 1


def test_an_empty_later_page_falls_back_to_the_first(neocities, monkeypatch):
    monkeypatch.setattr(transform.random, 'randint', lambda a, b: 4)
    neocities.answers = [b'<html>no sites</html>', PAGE]
    assert len(run()['items']) == 3 and neocities[1][0].endswith('page=1')


@pytest.mark.parametrize('failure', [socket.timeout(), urllib.error.URLError('down'),
                                     urllib.error.HTTPError('u', 503, 'busy', {}, None)])
def test_neocities_down_keeps_the_previous_sites(neocities, failure):
    neocities.answers = [failure]
    previous = {'items': [{'name': 'Old', 'url': 'https://old.neocities.org', 'image': 'x'}]}
    data = run(previous=previous)
    assert data['items'] == previous['items'] and 'unreachable' in data['stale_reason']
    neocities.answers = [failure]
    assert run() == {'items': [], 'error': data['stale_reason']}


def test_parses_the_earlier_markup_too():
    old = ('<a href="https://example.neocities.org" class="neo-Screen-Shot" title="Example Site">'
           '<span class="img-Holder" style="background:url(/site_screenshots/1/2/example/i.webp)"></span></a>')
    assert transform.parse_sites(old) == [{'name': 'Example Site', 'url': 'https://example.neocities.org',
                                           'image': 'https://neocities.org/site_screenshots/1/2/example/i.webp'}]
