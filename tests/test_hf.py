"""Tests for scps.hf mirror planning — no network, no token."""

from scps import hf


def _vintages():
    return {
        "concept_doi": "10.5281/zenodo.11098814",
        "vintages": {
            "V1": {
                "first_capture": "2024-08-02",
                "best_capture": "2024-08-02-1",
                "doi": "10.5281/zenodo.12685787",
            },
        },
    }


def _manifest():
    return {
        "tag": "2024-08-02-1",
        "files": [
            {
                "filename": "state_cancer_profiles_incidence.csv.gz",
                "sha256": "deadbeef",
                "bytes": 123,
                "rows": 4,
            },
        ],
    }


def test_render_card_leads_with_zenodo_citation():
    card = hf.render_card(_manifest(), "V1", _vintages())
    assert card.index("10.5281/zenodo.12685787") < card.index("## Files")
    assert "mirror" in card.lower()
    assert "No DOI is minted" in card
    assert "sha256: deadbeef" in card


def test_managed_filters_to_release_and_extra_files():
    assert hf._managed("state_cancer_profiles_incidence.csv.gz")
    assert hf._managed("manifest.json")
    assert hf._managed("README.md")
    assert not hf._managed("some_random_file.txt")
