"""Tests for scps.manifest — content hashing and vintage assignment."""

import gzip
import json
from pathlib import Path

import pandas as pd

from scps import manifest


def _write_release(tmp_path: Path, extracted_at: str, rate: str = "1.0") -> Path:
    rel = tmp_path / "rel"
    rel.mkdir(parents=True, exist_ok=True)
    for topic in ("incidence", "mortality"):
        df = pd.DataFrame(
            {
                "fips": ["01001", "01003"],
                "age_adjusted_rate_per_100_000": [rate, "2.0"],
                "_extracted_at": [extracted_at, extracted_at],
            }
        )
        df.to_csv(rel / f"state_cancer_profiles_{topic}.csv.gz", index=False, compression="gzip")
    (rel / "gh_hash.txt").write_text("abc123\n")
    return rel


def test_content_hash_ignores_extracted_at(tmp_path):
    a = _write_release(tmp_path / "a", "2026-01-01T00:00:00")
    b = _write_release(tmp_path / "b", "2026-02-01T09:30:00")
    ha, rows_a = manifest.content_hash(a / "state_cancer_profiles_incidence.csv.gz")
    hb, rows_b = manifest.content_hash(b / "state_cancer_profiles_incidence.csv.gz")
    assert ha == hb
    assert rows_a == rows_b == 2


def test_content_hash_differs_when_values_change(tmp_path):
    a = _write_release(tmp_path / "a", "2026-01-01T00:00:00", rate="1.0")
    b = _write_release(tmp_path / "b", "2026-01-01T00:00:00", rate="9.9")
    ha, _ = manifest.content_hash(a / "state_cancer_profiles_incidence.csv.gz")
    hb, _ = manifest.content_hash(b / "state_cancer_profiles_incidence.csv.gz")
    assert ha != hb


def test_build_manifest_covers_all_files(tmp_path):
    rel = _write_release(tmp_path, "2026-01-01T00:00:00")
    m = manifest.build_manifest(rel, "test-tag")
    assert m["tag"] == "test-tag"
    names = {f["filename"] for f in m["files"]}
    assert "state_cancer_profiles_incidence.csv.gz" in names
    assert "gh_hash.txt" in names
    assert set(m["content_hashes"]) == {"incidence", "mortality"}
    inc = next(f for f in m["files"] if f["filename"].endswith("incidence.csv.gz"))
    assert inc["rows"] == 2
    assert inc["format"] == "csv.gz"
    assert len(inc["sha256"]) == 64


def test_extract_notes_fields():
    notes = (
        "Incidence Rate Report\n"
        "Created by statecancerprofiles.cancer.gov on 08/23/2026 11:30 am.\n"
        '"(1) Source: NPCR and SEER. Based on the 2024 submission."\n'
        '"(7) Source: SEER November 2024 submission, based on the 2024 submission."\n'
    )
    fields = manifest.extract_notes_fields(notes)
    assert fields["created_on"] == "08/23/2026"
    assert fields["submission_years"] == ["2024"]


def _vintages(hash_inc, hash_mort):
    return {
        "vintages": {
            "V1": {
                "releases": ["t1"],
                "content_sha256": {"incidence": [hash_inc], "mortality": [hash_mort]},
            }
        }
    }


def test_assign_vintage_matches_existing(tmp_path):
    rel = _write_release(tmp_path, "2026-01-01T00:00:00")
    m = manifest.build_manifest(rel, "t2")
    vintages = _vintages(
        m["content_hashes"]["incidence"], m["content_hashes"]["mortality"]
    )
    vid, is_new = manifest.assign_vintage(m, vintages)
    assert (vid, is_new) == ("V1", False)


def test_assign_vintage_detects_new(tmp_path):
    rel = _write_release(tmp_path, "2026-01-01T00:00:00", rate="7.7")
    m = manifest.build_manifest(rel, "t2")
    vintages = _vintages("deadbeef", "deadbeef")
    vid, is_new = manifest.assign_vintage(m, vintages)
    assert (vid, is_new) == ("V2", True)
