"""Derived harmonized view across vintages.

This produces a NEW artifact from released files; original release bytes are
never modified (root CLAUDE.md). Harmonization decisions are data
(``data/crosswalks.json``), not code. The defects fixed here are the audit's
list in ``docs/schema-drift.md``:

- ``locale_type`` misclassification (derive from ``areatype`` + FIPS shape)
- footnote-prose rows leaked into demographics/risk (null keys → dropped)
- undecoded ``\\u00A0`` escapes and typos in race labels, plus a canonical
  race mapping for cross-topic joins where populations are identical
- the mangled RUCC column name
- ``(1)``/``(2)``/``(7)`` source markers embedded in ``reported_locale``

Accounting is strict: for every table, kept + dropped == original rows, and
``harmonize`` raises if not.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

CROSSWALKS_PATH = Path(__file__).resolve().parent.parent / "data" / "crosswalks.json"

_SOURCE_NOTE_RE = re.compile(r"\((\d+)\)\s*$")
_UNICODE_ESCAPE_RE = re.compile(r"\\u00a0", re.IGNORECASE)

# Key column per topic: rows with a null key are leaked footnote prose,
# not observations.
_KEY_COLUMN = {
    "incidence": "fips",
    "mortality": "fips",
    "risk": "fips",
    "demographics": "area_code",
}


def load_crosswalks(path: Path = CROSSWALKS_PATH) -> dict:
    return json.loads(path.read_text())


def clean_race(series: pd.Series, crosswalks: dict) -> tuple[pd.Series, pd.Series]:
    """Return (cleaned race label, canonical race label or <NA>)."""
    cleaned = (
        series.astype("string")
        .str.replace(_UNICODE_ESCAPE_RE, " ", regex=True)
        .str.replace("\u00a0", " ", regex=False)
        .str.strip()
        .replace(crosswalks.get("race_label_fixes", {}))
    )
    canonical = cleaned.map(crosswalks.get("race_canonical", {})).astype("string")
    return cleaned, canonical


def _fixed_locale_type(df: pd.DataFrame, key: str) -> pd.Series:
    """Re-derive locale_type from areatype + FIPS shape.

    The released ``locale_type`` bins 30-55k county-equivalents per release
    as ``other`` (parishes, boroughs, independent cities, DC) in everything
    before 2026-05-28. ``areatype`` is the request's source of truth.
    """
    code = df[key].astype("string").fillna("")
    out = pd.Series("other", index=df.index, dtype="string")
    is5 = code.str.len() == 5
    national = is5 & code.str.startswith("00")
    out[national] = "national"
    if "areatype" in df.columns:
        by_county = df["areatype"].astype("string").str.contains("County", na=False)
        by_state = df["areatype"].astype("string").str.contains("State", na=False)
        out[is5 & ~national & by_state] = "state"
        out[is5 & ~national & by_county & code.str.endswith("000")] = "state"
        out[is5 & ~national & by_county & ~code.str.endswith("000")] = "county"
    return out


def harmonize(
    df: pd.DataFrame, topic: str, vintage: str, tag: str, crosswalks: dict | None = None
) -> tuple[pd.DataFrame, int]:
    """Harmonize one topic table. Returns (harmonized, dropped_row_count).

    Raises ``AssertionError`` if kept + dropped != original (fail loudly,
    per SPEC M2).
    """
    crosswalks = crosswalks or load_crosswalks()
    original = len(df)
    key = _KEY_COLUMN[topic]

    df = df.rename(columns=crosswalks.get("column_renames", {}))

    leaked = df[key].isna()
    df = df[~leaked].copy()
    dropped = int(leaked.sum())

    if "race" in df.columns:
        df["race"], df["race_canonical"] = clean_race(df["race"], crosswalks)

    if "reported_locale" in df.columns:
        df["source_note"] = (
            df["reported_locale"].astype("string").str.extract(_SOURCE_NOTE_RE)[0]
        )

    df["locale_type"] = _fixed_locale_type(df, key)
    df["vintage"] = vintage
    df["release_tag"] = tag

    assert len(df) + dropped == original, (
        f"{topic}: {len(df)} kept + {dropped} dropped != {original} original"
    )
    return df, dropped


def harmonize_release(
    release_dir: Path, vintage: str, tag: str, crosswalks: dict | None = None
) -> dict[str, tuple[pd.DataFrame, int]]:
    """Harmonize every topic file present in a downloaded release directory."""
    crosswalks = crosswalks or load_crosswalks()
    out: dict[str, tuple[pd.DataFrame, int]] = {}
    for topic in _KEY_COLUMN:
        path = release_dir / f"state_cancer_profiles_{topic}.csv.gz"
        if not path.exists():
            continue
        df = pd.read_csv(path, dtype=str, low_memory=False)
        out[topic] = harmonize(df, topic, vintage, tag, crosswalks)
    return out
