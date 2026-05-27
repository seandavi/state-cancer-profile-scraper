"""Pre-import the scps.scraper module under a mocked httpx.get.

``scps.scraper.get_select_options()`` runs at module import time and would
otherwise hit the live State Cancer Profiles website. We force the import
here, with httpx patched, before any test module loads. After the import,
the patch is released so individual tests can patch httpx themselves.
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

_httpx_patch = patch("httpx.get", return_value=_mock_response)
_httpx_patch.start()
try:
    import scps.scraper  # noqa: F401  (force module load while patched)
finally:
    _httpx_patch.stop()
