# AOM contributor instructions

## Research boundary

AOM owns research/references, variants, generic benchmarks/examples and the WASM demo; production numerics belong in Methods/public C ABI.
`aom_nirs` stays independently versioned reference during consolidation; move/removal needs a separate decision. Preserve distinct AOM-PLS/Ridge/Ridge-PLS/FastAOM contracts/tolerances: family names prove no parity. Never rewrite frozen reproductions/goldens for green.
Manuscripts/supplements/reviewer controls, frozen paper cohorts/partitions and results stay private until submission, not installed here. No cohort-read or paper/publication-archive/output authority.
Use explicit data/output paths; no production import from manuscript/reviewer-control directories. Cleanup grants no publication/history rewrite.

## Experiments, gates and rights

From checkout/package env follow [REPRODUCTION](REPRODUCTION.md): bench/dev install, family tests, synthetic smoke are future gates, not executed here.
Use [benchmark rules](docs/benchmark_protocol.md), [records](docs/reproducibility.md), [runner conditions](benchmarks/README.md), [splitters](docs/aom_panoply.md#explicit-cv-splitters) and [candidate defaults](docs/aom_panoply.md#practical-candidate-set).
`python scripts/check_private_artifacts.py` is a future authorized boundary check, not executed evidence. Ignored benchmarks/runs/workspaces are not exempt; use external outputs. History redaction/release is separate.
Keep [LICENSING](LICENSING.md)/[upstream notices](THIRD_PARTY_NOTICES.md): `CeCILL-2.1 OR AGPL-3.0-or-later`, optional commercial contact, SPDX and upstream rights.

## Working rules

Read applicable instructions first and preserve dirty work. If `../AGENTS.md` exists, read it within the current user scope; this file also works alone.
Use CodeGraph FIRST only with this checkout's own `.codegraph/` (exact projectPath or local CLI); never auto-index or use an ancestor index. Source, tests and builds are final authority.
Record actual commands, exits and skips. Keep secrets, private data and build output out of Git. Examples grant no install, network, science, publication, hosting, frontend or Git authority.
All project content, including UI text, docs, tests, reports, PRs and commits, is English; conversation may be French. Preserve names, identifiers, quotations and provenance.
