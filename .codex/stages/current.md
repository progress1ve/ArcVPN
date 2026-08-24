# Current stage: local cleanup and node operations

Status: ready for closeout

## Goal

Make the repository root intentional and make future node/CDN operations reproducible without putting credentials in Git.

## Non-goals

- No production topology, subscription, database, or runtime behavior changes.
- No deletion of active source or assets merely because they are old.
- No plaintext credentials in tracked files.

## Component map

- Root tracked files and ignored local artifacts.
- Documentation and operational scripts referenced from code/docs/systemd.
- `.gitignore`, local secret storage convention, and a non-secret server inventory.
- New `.agents/skills/arcvpn-node-ops/` skill and node configuration contract.

## Acceptance

- Every root file is classified as root entrypoint, source, asset, documentation, operations, generated, obsolete, secret, or unknown.
- Proven obsolete/generated files are removed; retained material has a clear directory and updated references.
- Root contains only genuine project entrypoints/configuration.
- Node/CDN skill covers discovery, credential lookup, provisioning gates, Remnawave binding, LTE/XHTTP/CDN specifics, rollback, and evidence.
- Credentials remain local and ignored; the project contains a documented mechanism and non-secret inventory schema.
- Git diff has no secrets; relevant Python/import/link checks pass.

## Risks and rollback

- Moving files can break imports, service installation, or documentation links. Search callers before moving and update all tracked references in the same commit.
- Deleting diagnostics can remove historical convenience. Delete only generated/backup/obsolete classes; Git-tracked moves remain recoverable from history.
- Rollback is `git revert` of the cleanup commit. Local ignored secret files are not modified without an explicit exact target.

## Verification matrix

- Structure: root inventory and `git status`.
- References: targeted `rg` for every moved basename.
- Python: compile/import tests for affected runtime modules.
- Skills: frontmatter/contract validation.
- Security: staged secret-pattern scan.
- Production: documentation/structure-only pull; no service restart unless runtime paths change.

## Acceptance results

- Passed — root classification is recorded in `docs/operations/repository-layout.md`.
- Passed — unused SVGs, old screenshot/backup, one-off agent scripts, caches, logs, and obsolete video diagnostics were removed.
- Passed — roadmaps, archive documents, UI references, systemd units, and operational scripts have explicit homes; references and usage examples were updated.
- Passed — `$arcvpn-node-ops` covers node lifecycle and conditional CDN/LTE details through progressive references.
- Passed — `.codex/server-inventory.toml` contains aliases/topology only; `scripts/ops/server-vault.ps1` stores DPAPI-encrypted credentials under ignored `.secrets/`.
- Passed — TOML and PowerShell syntax checks succeeded; 12 affected/runtime Python files passed `py_compile`; `git diff --check` succeeded.
- Deferred — actual vault entries require the owner to type current passwords into secure prompts. No credential was copied from chat history.

## Residual risks

- Archived 3x-ui scripts are retained for rollback/history and must not be treated as current Remnawave tooling.
- DPAPI vault files work only for the same Windows user on this machine; maintain a separate recoverable owner password source.
- Production pull requires a populated `pl-control` vault entry or SSH key.

## Next step

Populate `pl-control`, `de-dhost`, and `nl-dhost` credentials using the secure prompts, then verify read-only SSH access through the node-operations workflow.
