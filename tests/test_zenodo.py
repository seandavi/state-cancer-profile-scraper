"""Tests for scps.zenodo deposit planning — no network, no token."""

from pathlib import Path

from scps import zenodo


def _vintages():
    return {
        "vintages": {
            "V1": {
                "releases": ["2024-08-02-1"],
                "first_capture": "2024-08-02",
                "best_capture": "2024-08-02-1",
                "content_sha256": {"incidence": ["a"], "mortality": ["b"]},
            },
            "V2": {
                "releases": ["2025-02-10", "2025-03-01"],
                "first_capture": "2025-02-10",
                "best_capture": "2025-03-01",
                "content_sha256": {"incidence": ["c"], "mortality": ["d"]},
            },
        }
    }


def _release_root(tmp_path: Path) -> Path:
    for tag in ("2024-08-02-1", "2025-03-01"):
        d = tmp_path / tag
        d.mkdir(exist_ok=True)
        (d / "state_cancer_profiles_incidence.csv.gz").write_bytes(b"x")
    return tmp_path


def _version(tag: str) -> dict:
    return {
        "id": 1,
        "metadata": {
            "publication_date": "2024-08-02",
            "related_identifiers": [
                {
                    "identifier": f"https://github.com/seandavi/state-cancer-profile-scraper/releases/tag/release-{tag}",
                    "relation": "isSupplementTo",
                }
            ],
        },
    }


def test_plan_backfill_oldest_first_and_uses_best_capture(tmp_path):
    plan = zenodo.plan_backfill(_vintages(), _release_root(tmp_path), [])
    assert [d.vintage_id for d in plan] == ["V1", "V2"]
    v2 = plan[1]
    assert v2.publication_date == "2025-02-10"      # first capture dates it
    assert v2.best_capture == "2025-03-01"          # best capture supplies bytes
    assert v2.files and v2.files[0].parent.name == "2025-03-01"


def test_plan_backfill_is_idempotent(tmp_path):
    existing = [_version("2024-08-02-1")]
    plan = zenodo.plan_backfill(_vintages(), _release_root(tmp_path), existing)
    assert [d.vintage_id for d in plan] == ["V2"]
    # All tags deposited → empty plan.
    plan2 = zenodo.plan_backfill(
        _vintages(), _release_root(tmp_path), [_version("2024-08-02-1"), _version("2025-02-10")]
    )
    assert plan2 == []


def test_vintage_metadata_carries_identity_and_tags(tmp_path):
    plan = zenodo.plan_backfill(_vintages(), _release_root(tmp_path), [])
    md = zenodo.vintage_metadata(plan[1])
    assert md["publication_date"] == "2025-02-10"
    assert md["license"] == "cc-by-4.0"
    assert md["upload_type"] == "dataset"
    idents = [r["identifier"] for r in md["related_identifiers"]]
    assert any("release-2025-02-10" in i for i in idents)
    assert any("release-2025-03-01" in i for i in idents)
    assert "vintage V2" in md["title"]
    # The description states the best-vs-first capture distinction.
    assert "most" in md["description"] and "first" in md["description"]


def test_deposited_tags_parses_related_identifiers():
    tags = zenodo.deposited_tags([_version("2025-02-10"), _version("2024-08-02-1")])
    assert tags == {"2025-02-10", "2024-08-02-1"}


def test_run_deposit_dry_run_touches_nothing():
    dep = zenodo.VintageDeposit(
        vintage_id="V1", tags=["t"], publication_date="2024-08-02",
        best_capture="t", files=[],
    )
    client = zenodo.ZenodoClient("https://example.invalid", "no-token")
    assert zenodo.run_deposit(client, "0", dep, dry_run=True) is None
