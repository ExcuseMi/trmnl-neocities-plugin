import hashlib
import io
import logging

import aiohttp
from PIL import Image

log = logging.getLogger(__name__)

_CACHE_PREFIX = 'neocities:edge:v1:'
_CACHE_TTL = 7 * 86400  # 7 days — screenshots change rarely


def _compute(data: bytes) -> str:
    img = Image.open(io.BytesIO(data)).convert('RGB')
    w, h = img.size
    px = list(img.getdata())

    edge = (
        px[:w]                                          # top row
        + px[(h - 1) * w:]                             # bottom row
        + [px[i * w] for i in range(1, h - 1)]         # left col
        + [px[i * w + w - 1] for i in range(1, h - 1)] # right col
    )

    n = len(edge)
    r = sum(p[0] for p in edge) // n
    g = sum(p[1] for p in edge) // n
    b = sum(p[2] for p in edge) // n
    return f'#{r:02x}{g:02x}{b:02x}'


async def get_edge_color(image_url: str, session: aiohttp.ClientSession, redis) -> str | None:
    key = _CACHE_PREFIX + hashlib.sha1(image_url.encode()).hexdigest()

    try:
        cached = await redis.get(key)
        if cached:
            return cached
    except Exception:
        pass

    try:
        async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            resp.raise_for_status()
            data = await resp.read()
        color = _compute(data)
        try:
            await redis.set(key, color, ex=_CACHE_TTL)
        except Exception:
            pass
        return color
    except Exception as exc:
        log.warning('Edge color unavailable for %s: %s', image_url, exc)
        return None
