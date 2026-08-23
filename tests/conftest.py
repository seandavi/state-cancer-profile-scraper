"""Prime the cached select-option vocabulary under a mocked httpx.get.

``scps.scraper.select_options()`` is fetched lazily and cached (no network
at import time — #37). Tests that exercise ``get_table`` need the vocabulary
populated, so we prime the cache here with a small fixture while httpx is
patched. Individual tests can still patch httpx themselves.
"""

from unittest.mock import MagicMock, patch

MOCK_SELECT_HTML = """
<html>
<body>
  <select id="cancer">
    <option value="001">All Cancer Sites</option>
    <option value="071">Bladder</option>
  </select>
  <select id="year">
    <option value="0">Latest 5-year average</option>
  </select>
  <select id="race">
    <option value="00">All Races (includes Hispanic)</option>
  </select>
  <select id="sex">
    <option value="0">Both Sexes</option>
    <option value="1">Male</option>
    <option value="2">Female</option>
  </select>
  <select id="age">
    <option value="001">All Ages</option>
  </select>
  <select id="stage">
    <option value="999">All Stages</option>
  </select>
  <select id="areatype">
    <option value="county">By County</option>
    <option value="state">By State/Registry/Division</option>
  </select>
</body>
</html>
"""

_mock_response = MagicMock()
_mock_response.text = MOCK_SELECT_HTML

with patch("httpx.get", return_value=_mock_response):
    import scps.scraper

    scps.scraper.select_options()  # populate the lru_cache under the mock
