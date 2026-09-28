# AOM repository boundaries

- This repository owns AOM research, experimental variants, generic benchmark
  tooling, examples and the WebAssembly demonstration.
- Stable production methods and their shared numerical engine belong in the
  sibling `nirs4all-methods` repository. Its bindings call the public C ABI.
- The existing `aom_nirs` implementation remains an independently versioned
  Python reference during consolidation. Preserve numerical contracts when
  optimizing it; do not silently equate distinct Ridge-PLS or FastAOM variants.
- Manuscripts, supplements, submission packages, editorial reviews and
  paper-specific protocols/results belong exclusively in the private sibling
  `nirs4all-drafts/aom_talanta_26` until submission. Do not recreate `paper/`,
  publication archives or paper-specific benchmark outputs here.
- Use explicit data and output paths for generic benchmarks. Production code
  must not import anything from a manuscript/reviewer-control directory.
- Do not publish or rewrite Git history as a side effect of local cleanup.
- When `.codegraph/` exists, query CodeGraph before locating indexed code;
  direct source and tests remain authoritative.
