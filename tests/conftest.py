"""Configure pytest and mock the module-level HTTP call in scps.scraper.

scps.scraper calls get_select_options() at import time (module level), which
makes a real HTTP request.  We intercept that request here via pytest hooks so
that the module is only imported once with a mocked httpx.get and the test suite
can run fully offline.
"""

from unittest.mock import MagicMock, patch

import pytest

from tests._mock_data import MOCK_SELECT_HTML

_mock_response = MagicMock()
_mock_response.text = MOCK_SELECT_HTML

_patched_httpx_get = None


def pytest_configure(config):
    """Patch httpx.get and import scps.scraper once for the whole test run."""
    global _patched_httpx_get

    if _patched_httpx_get is not None:
        # Already configured (can happen if conftest is imported more than once).
        return

    _patched_httpx_get = patch("httpx.get", return_value=_mock_response)
    _patched_httpx_get.start()

    # Import scps.scraper after httpx.get is patched so its module-level
    # get_select_options() call uses the mock instead of performing I/O.
    import scps.scraper  # noqa: F401


def pytest_unconfigure(config):
    """Undo the httpx.get patch applied in pytest_configure."""
    global _patched_httpx_get

    if _patched_httpx_get is not None:
        _patched_httpx_get.stop()
        _patched_httpx_get = None


@pytest.fixture()
def mock_select_response():
    """Return a mock httpx response whose .text is MOCK_SELECT_HTML."""
    resp = MagicMock()
    resp.text = MOCK_SELECT_HTML
    return resp
