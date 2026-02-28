"""Configure pytest and mock the module-level HTTP call in scps.scraper.

scps.scraper calls get_select_options() at import time (module level), which
makes a real HTTP request.  We intercept that request here – before any test
module imports scps.scraper – so the test suite can run fully offline.
"""

from unittest.mock import MagicMock, patch

import pytest

# Minimal HTML that satisfies get_select_options() parsing.
# Defined once here and shared with test modules via the fixture below.
MOCK_SELECT_HTML = """
<html>
<body>
  <select id="cancer">
    <option value="001">All Cancer Sites Combined</option>
  </select>
  <select id="year">
    <option value="0">Latest 5 Year Average</option>
  </select>
  <select id="race">
    <option value="00">All Races</option>
  </select>
  <select id="sex">
    <option value="0">Both Sexes</option>
  </select>
  <select id="areatype">
    <option value="county">County</option>
  </select>
  <select id="stage">
    <option value="999">All Stages</option>
  </select>
  <select id="age">
    <option value="001">All Ages</option>
  </select>
</body>
</html>
"""

_mock_response = MagicMock()
_mock_response.text = MOCK_SELECT_HTML

# Patch httpx.get so that the module-level get_select_options() call in
# scps.scraper does not perform a real network request.
with patch("httpx.get", return_value=_mock_response):
    import scps.scraper  # noqa: F401


@pytest.fixture()
def mock_select_response():
    """Return a mock httpx response whose .text is MOCK_SELECT_HTML."""
    resp = MagicMock()
    resp.text = MOCK_SELECT_HTML
    return resp
