import html as html_module
import logging
import os
import re

import aiohttp

from .base import BaseProvider

log = logging.getLogger(__name__)

_BROWSE_URL = 'https://neocities.org/browse?sort_by={sort_by}&tag=&page={page}'
_PAGES = int(os.getenv('NEOCITIES_PAGES', '5'))
_RE_SITE = re.compile(
    r'<a\s+href="([^"]+)"\s+class="neo-Screen-Shot"\s+title="([^"]+)"'
    r'[^>]*>[\s\S]*?<span[^>]+style="background:url\(([^)]+)\)',
)
_HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; TRMNL/1.0)'}


class NeocitiesProvider(BaseProvider):
    async def _fetch(self, sort_by: str = 'special_sauce', **_) -> list[dict] | None:
        sites: list[dict] = []
        seen: set[str] = set()

        async with aiohttp.ClientSession(headers=_HEADERS) as session:
            for page in range(1, _PAGES + 1):
                url = _BROWSE_URL.format(sort_by=sort_by, page=page)
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        status = resp.status
                        resp.raise_for_status()
                        text = await resp.text()
                    log.debug('Neocities page %d (sort=%s) HTTP %d len=%d', page, sort_by, status, len(text))
                except Exception as exc:
                    log.warning('Neocities page %d (sort=%s) failed: %s', page, sort_by, exc)
                    continue

                page_count = 0
                for m in _RE_SITE.finditer(text):
                    site_url = m.group(1)
                    if site_url in seen:
                        continue
                    seen.add(site_url)
                    name = html_module.unescape(m.group(2))
                    path = m.group(3)
                    image = ('https://neocities.org' + path) if path.startswith('/') else path
                    sites.append({'name': name, 'url': site_url, 'image': image})
                    page_count += 1
                if page_count == 0:
                    log.warning('Neocities page %d (sort=%s) returned 0 matches — possible block/redirect (len=%d)', page, sort_by, len(text))

        log.info('Scraped %d unique sites (sort_by=%s, pages=%d)', len(sites), sort_by, _PAGES)
        return sites if sites else None
