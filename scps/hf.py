"""Hugging Face dataset mirror for the vintage archive (SPEC M6).

Additive to Zenodo, never authoritative: no DOI minted here, and the
dataset card leads with the Zenodo concept DOI as the citable identity.
The mirror lives on ``main``; each vintage's commit is tagged
``zenodo-vN`` so history stays git-native instead of duplicated into
per-vintage folders (SPEC M6: "HF git tags carry no citational meaning
... name them after the Zenodo version they mirror").
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from huggingface_hub import CommitOperationAdd, CommitOperationDelete, HfApi

from scps.manifest import RELEASE_FILE_RE, _blurb

REPO_ID = "seandavis/state-cancer-profiles"

# Filenames this routine owns on the HF repo; only these are ever added or
# deleted by a mirror commit, so anything else manually added is untouched.
_MANAGED_EXTRA = {"manifest.json", "00_README.md", "README.md"}


def _managed(filename: str) -> bool:
    return bool(RELEASE_FILE_RE.match(filename)) or filename in _MANAGED_EXTRA


def render_card(manifest: dict, vid: str, vintages: dict) -> str:
    """Dataset card (README.md): leads with the Zenodo concept DOI as the
    citable identity, states plainly this is a mirror, lists every file's
    sha256 (must match the manifest, per SPEC M6)."""
    info = vintages["vintages"][vid]
    doi = info.get("doi", "(pending)")
    concept = vintages.get("concept_doi", "10.5281/zenodo.11098814")
    lines = [
        "---",
        "license: cc-by-4.0",
        "---",
        "",
        "# United States State Cancer Profiles data extract (mirror)",
        "",
        "**This is a mirror. Cite the Zenodo record, not this page:**",
        "",
        f"> Davis S. *United States State Cancer Profiles data extract — "
        f"vintage {vid}.* Zenodo. https://doi.org/{doi}",
        "",
        "Concept DOI (always resolves to the latest vintage): "
        f"https://doi.org/{concept}",
        "",
        "No DOI is minted on Hugging Face. HF hosts these bytes for native "
        "`hf://` / DuckDB access and an ML audience that would never find "
        "the Zenodo record; Zenodo is the archival and citable copy. Git "
        "tags on this repo are named `zenodo-vN` to match the Zenodo "
        "version they mirror — they carry no citational meaning of their "
        "own.",
        "",
        "## Provenance",
        "",
        f"- **Vintage:** {vid} (first captured {info['first_capture']})",
        f"- **Mirrored bytes:** GitHub release `{info['best_capture']}`",
        "- **Source repository:** "
        "https://github.com/seandavi/state-cancer-profile-scraper",
        "- **License:** CC-BY-4.0",
        "",
        "## Files",
        "",
    ]
    for f in manifest["files"]:
        rows = f", {f['rows']:,} rows" if "rows" in f else ""
        lines.append(f"**{f['filename']}** ({f['bytes']:,} bytes{rows})  ")
        lines.append(f"`sha256: {f['sha256']}`")
        blurb = _blurb(f["filename"])
        if blurb:
            lines.append("")
            lines.extend(textwrap.wrap(blurb, width=78))
        lines.append("")
    return "\n".join(lines) + "\n"


def mirror_vintage(
    release_dir: Path,
    files: list[Path],
    vid: str,
    vintages: dict,
    manifest: dict,
    repo_id: str = REPO_ID,
    token: str | None = None,
) -> str:
    """Mirror one vintage's release files to the HF dataset repo.

    ``files`` are the release artifacts already on disk in ``release_dir``
    (same set as the Zenodo deposit, e.g. ``manifest_mod.release_files(...)
    + [manifest.json, 00_README.md]``). Writes the dataset card alongside
    them, clears any stale managed files from a prior vintage (a vintage
    transition can drop a topic or format), commits, and tags the commit
    ``zenodo-vN``. Returns the tag name.
    """
    api = HfApi(token=token)
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True, token=token)

    card = release_dir / "README.md"
    card.write_text(render_card(manifest, vid, vintages))
    wanted = {p.name: p for p in [*files, card]}

    existing = {
        f for f in api.list_repo_files(repo_id, repo_type="dataset")
        if _managed(f)
    }
    ops = [
        CommitOperationAdd(path_in_repo=name, path_or_fileobj=str(path))
        for name, path in wanted.items()
    ] + [
        CommitOperationDelete(path_in_repo=name)
        for name in existing - wanted.keys()
    ]

    api.create_commit(
        repo_id, operations=ops, repo_type="dataset",
        commit_message=f"Vintage {vid} — {manifest['tag']}", token=token,
    )
    tag = f"zenodo-v{int(vid.lstrip('V'))}"
    api.create_tag(repo_id, tag=tag, repo_type="dataset", exist_ok=True, token=token)
    return tag
