# scripts/hf/ — Hugging Face mirror conventions

Target: dataset repo `seandavis/state-cancer-profiles`. Mirror only, never
authoritative — no DOI minted here. Zenodo concept `10.5281/zenodo.11098814`
is the citable identity; the HF dataset card leads with it.

One commit per vintage on `main`, tagged `zenodo-vN` to match the Zenodo
version it mirrors (never a bare `vN` — that would read as citable). The
logic lives in `scps/hf.py` (`mirror_vintage`, `render_card`); this
directory holds only the runnable entry points, same split as
`scripts/zenodo/` vs `scps/zenodo.py`.

- Mirroring only follows an actual Zenodo publish of a **new vintage** — the
  same gate `publish_release.py` uses for Zenodo itself (SPEC M6: "Zenodo
  publishes first, then mirrors"). Re-scrapes of an already-deposited
  vintage don't touch either host.
- Never mirror a `--sandbox` Zenodo rehearsal to the real HF repo.
- Token: `HF_TOKEN` (env, CI secret). No GSM lookup wired yet — unlike
  Zenodo's `cdsci-zenodo-api-token`, this repo doesn't yet have an
  `hf_hub_download`-style GSM secret; add one (`cdsci-hf-api-token`,
  project `cdsci-infra`) if the env-var convention needs to change.
- `scripts/hf/backfill.py` verifies every downloaded byte's sha256 against
  the manifest already committed at `manifests/<tag>.json` before mirroring
  — never trust a re-download without checking it against the record.
