import asyncio
import logging
import os
import random

import aiohttp
from quart import Quart, jsonify, request
from redis.asyncio import Redis

from modules.providers.neocities import NeocitiesProvider
from modules.utils.edge_color import get_edge_color
from modules.utils.ip_whitelist import init_ip_whitelist, require_tiered_access

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
log = logging.getLogger(__name__)

app = Quart(__name__)

REFRESH_HOURS = float(os.getenv('REFRESH_HOURS', '0.5'))
SITES_PER_REQUEST = int(os.getenv('SITES_PER_REQUEST', '4'))
_VALID_SORT = frozenset({
    'special_sauce', 'random', 'most_followed', 'last_updated',
    'views', 'tipping_enabled', 'oldest',
})

_redis = Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', '6379')),
    db=0,
    decode_responses=True,
)
_provider = NeocitiesProvider(name='neocities', redis=_redis)


@app.before_serving
async def _startup():
    await init_ip_whitelist()
    log.info('Neocities backend started — cache TTL %.1fh', REFRESH_HOURS)


@app.route('/sites')
@require_tiered_access(lambda: _redis, prefix='sites')
async def sites():
    sort_by = request.args.get('sort_by', 'special_sauce').strip()
    if sort_by not in _VALID_SORT:
        sort_by = 'special_sauce'

    ttl = REFRESH_HOURS * 3600
    kwargs = dict(sort_by=sort_by)

    expired = await _provider.is_expired(ttl, **kwargs)
    if expired:
        cached = await _provider.get_cached(**kwargs)
        if cached:
            log.info('sites: cache stale (sort=%s pool=%d) — serving stale, refreshing async', sort_by, len(cached))
            asyncio.create_task(_provider.refresh(**kwargs))
        else:
            log.info('sites: cache cold (sort=%s) — blocking fetch', sort_by)
            cached = await _provider.refresh(**kwargs)
    else:
        cached = await _provider.get_cached(**kwargs)
        log.info('sites: cache hit (sort=%s pool=%d)', sort_by, len(cached) if cached else 0)

    if not cached:
        log.error('sites: no data available (sort=%s) — returning 503', sort_by)
        return jsonify({'error': 'Neocities unreachable'}), 503

    selected = [dict(s) for s in random.sample(cached, min(SITES_PER_REQUEST, len(cached)))]
    async with aiohttp.ClientSession() as session:
        colors = await asyncio.gather(*[
            get_edge_color(s['image'], session, _redis) for s in selected
        ])
    color_count = 0
    for site, color in zip(selected, colors):
        if color:
            site['bg_color'] = color
            color_count += 1

    log.info('sites: returning %d sites, %d with bg_color (sort=%s)', len(selected), color_count, sort_by)
    return jsonify({'data': selected})


@app.route('/health')
async def health():
    try:
        await _redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return jsonify({'ok': True, 'redis': redis_ok})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
