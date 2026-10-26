# TRMNL serverless (Python): four random Neocities sites as `items`, read straight from neocities.org/browse.
# Standard library only, as TRMNL's sandbox offers. Replaces the backend on trmnl.bettens.dev (2026-10-26):
# one page per refresh instead of five, and no edge colour (the sandbox cannot decode WebP screenshots).

import html
import random
import re
import time
import urllib.request

BROWSE_URL = 'https://neocities.org/browse?sort_by={sort_by}&tag=&page={page}'
SORTS = ('special_sauce', 'random', 'most_followed', 'last_updated', 'views', 'tipping_enabled', 'oldest')
PAGES = 5  # a random one of the first five pages: variety for the fixed sorts, one request per refresh
SITES = 4
TIMEOUT_SECONDS = 3.5  # TRMNL stops a run after 5 s; the rest is margin for the sandbox start
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; TRMNL/1.0)'}
# One site on the browse page; both the markup before 2026-10-25 (background:url) and after it (background-image:url,
# a title over several lines)
SITE = re.compile(
    r'<a\s+href="([^"]+)"\s+class="neo-Screen-Shot"\s+title="([^"]+)"'
    r'[^>]*>[\s\S]*?<span[^>]+style="background(?:-image)?\s*:\s*url\(([^)]+)\)',
)


def parse_sites(text):
    """The sites on one browse page: name, url and screenshot"""
    sites, seen = [], set()
    for m in SITE.finditer(text):
        if m.group(1) in seen:
            continue
        seen.add(m.group(1))
        path = m.group(3).strip('\'"')
        sites.append({'name': ' '.join(html.unescape(m.group(2)).split()), 'url': m.group(1),
                      'image': ('https://neocities.org' + path) if path.startswith('/') else path})
    return sites


def fetch_page(sort_by, page, timeout):
    request = urllib.request.Request(BROWSE_URL.format(sort_by=sort_by, page=page), headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(2_000_000).decode('utf-8', errors='replace')


def run(input):
    started = time.monotonic()
    trmnl = input.get('trmnl') or {}
    values = (trmnl.get('plugin_settings') or {}).get('custom_fields_values') or {}
    sort_by = values.get('sort_by') if values.get('sort_by') in SORTS else 'special_sauce'
    page = random.randint(1, PAGES)
    try:
        sites = parse_sites(fetch_page(sort_by, page, TIMEOUT_SECONDS))
        if not sites and page != 1:  # fewer pages than five for this sort: the first always has sites
            sites = parse_sites(fetch_page(sort_by, 1, max(0.5, TIMEOUT_SECONDS - (time.monotonic() - started))))
        error = None if sites else 'Neocities returned no sites'
    except Exception as exc:  # timeout, network, HTTP error: show the previous sites instead of an empty screen
        sites, error = [], f'Neocities unreachable ({type(exc).__name__})'
    if sites:
        return {'items': random.sample(sites, min(SITES, len(sites)))}
    previous = trmnl.get('previous_merge_variables') or {}
    if previous.get('items'):
        return {**previous, 'stale_reason': error}
    return {'items': [], 'error': error}
