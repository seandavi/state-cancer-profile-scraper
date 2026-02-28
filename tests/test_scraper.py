"""Basic tests for scps.scraper using pytest."""

from unittest.mock import MagicMock, patch

import pytest

from scps.scraper import column_text_replace, get_select_options
from tests._mock_data import MOCK_SELECT_HTML


# ---------------------------------------------------------------------------
# column_text_replace
# ---------------------------------------------------------------------------


class TestColumnTextReplace:
    def test_brackets_removed(self):
        assert column_text_replace("[note]") == "note"

    def test_parens_removed(self):
        assert column_text_replace("(note)") == "note"

    def test_spaces_to_underscores(self):
        assert column_text_replace("hello world") == "hello_world"

    def test_percent_to_pct(self):
        assert column_text_replace("50%") == "50pct"

    def test_asterisk_to_underscore(self):
        assert column_text_replace("test*note") == "test_note"

    def test_lowercase(self):
        assert column_text_replace("TEST") == "test"

    def test_strips_whitespace(self):
        assert column_text_replace("  test  ") == "test"

    def test_hyphen_to_underscore(self):
        assert column_text_replace("age-adjusted") == "age_adjusted"

    def test_comma_to_underscore(self):
        assert column_text_replace("a,b") == "a_b"

    def test_dot_to_underscore(self):
        assert column_text_replace("v1.2") == "v1_2"

    def test_question_mark_removed(self):
        assert column_text_replace("test?") == "test"

    def test_complex_column_name(self):
        """Column names from the actual CSV should be made safe / lowercase."""
        col = "Age-Adjusted Incidence Rate[rate note] (cases per 100,000)"
        result = column_text_replace(col)
        assert " " not in result
        assert "[" not in result
        assert "(" not in result
        assert result == result.lower()


# ---------------------------------------------------------------------------
# get_select_options
# ---------------------------------------------------------------------------


class TestGetSelectOptions:
    def test_returns_dict(self, mock_select_response):
        with patch("httpx.get", return_value=mock_select_response):
            result = get_select_options()
        assert isinstance(result, dict)

    def test_expected_keys_present(self, mock_select_response):
        with patch("httpx.get", return_value=mock_select_response):
            result = get_select_options()
        for key in ("cancer", "year", "race", "sex", "areatype", "stage", "age"):
            assert key in result, f"Missing key: {key}"

    def test_cancer_option_value(self, mock_select_response):
        with patch("httpx.get", return_value=mock_select_response):
            result = get_select_options()
        assert result["cancer"]["001"] == "All Cancer Sites Combined"

    def test_age_pediatric_options_added(self, mock_select_response):
        """get_select_options() hard-codes two extra pediatric age groups."""
        with patch("httpx.get", return_value=mock_select_response):
            result = get_select_options()
        assert result["age"]["016"] == "Age < 15"
        assert result["age"]["015"] == "Age < 20"

    def test_separator_options_excluded(self):
        """Options whose text starts with '---' should be skipped."""
        html_with_separator = MOCK_SELECT_HTML.replace(
            '<option value="001">All Cancer Sites Combined</option>',
            '<option value="---">--- Select ---</option>'
            '<option value="001">All Cancer Sites Combined</option>',
        )
        resp = MagicMock()
        resp.text = html_with_separator
        with patch("httpx.get", return_value=resp):
            result = get_select_options()
        assert "---" not in result["cancer"]
