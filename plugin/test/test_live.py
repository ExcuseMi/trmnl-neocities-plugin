# Asks neocities.org itself: catches the next markup change. Run: LIVE=1 python3 -m pytest plugin/test
import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'src'))
import transform  # noqa: E402

pytestmark = pytest.mark.skipif(not os.getenv('LIVE'), reason='set LIVE=1 to ask neocities.org')


@pytest.mark.parametrize('sort_by', transform.SORTS)
def test_every_sort_gives_sites(sort_by):
    items = transform.run({'trmnl': {'plugin_settings': {'custom_fields_values': {'sort_by': sort_by}}}})['items']
    assert len(items) == transform.SITES
    assert all(s['image'].startswith('https://neocities.org/site_screenshots/') for s in items)
