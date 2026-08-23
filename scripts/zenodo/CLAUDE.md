# scripts/zenodo/ — deposit conventions and API gotchas

Target: **data** concept `10.5281/zenodo.11098814` (CC-BY-4.0). One version per vintage
(V1/V2/V3 …, mapping in docs/releases.md), oldest first, deposit best-capture bytes,
`publication_date` = first capture. Never touch the webhook-maintained software concept
`10.5281/zenodo.13174526`. Idempotency key: the GitHub release tags in
`related_identifiers` — re-running must not create duplicates.

**Rehearse everything on sandbox.zenodo.org first.** Published Zenodo records cannot be
deleted. Sandbox is a separate instance (separate account, token, and concept — a
throwaway one); production and sandbox differ by exactly two config values (base URL,
concept id) plus the token.

## API gotchas

- New version = `POST /deposit/depositions/{id}/actions/newversion`, then work against the
  *draft* in `links.latest_draft`, not the original id.
- Files do not carry over usefully to a new version — clear and re-upload.
- `publication_date` is settable any time before publish; after publish, metadata is
  editable but files are not.
- Rate limits are modest: upload sequentially with retry/backoff, never concurrently.
- Tokens come from GCP Secret Manager (`cdsci-zenodo-api-token`,
  `cdsci-zenodo-sandbox-api-token`, project `cdsci-infra`), overridable via
  `ZENODO_TOKEN` for CI. Never hardcode or log them.
