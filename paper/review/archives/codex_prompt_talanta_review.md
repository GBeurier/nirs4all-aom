# Codex — Full Talanta-targeted review of the AOM paper

Working directory: `/home/delete/nirs4all/nirs4all`. **READ-ONLY
on the paper sources.** You may only write the output document
under `paper_aom/review/`.

## Your role

You are an independent expert reviewer for *Talanta* (Elsevier,
analytical chemistry / chemometrics, IF ≈ 6.0). Read the AOM
paper (main + supplement + every supporting artifact) and write
a **complete review document** that the authors will use to bring
the paper to acceptance standard.

The user, verbatim:
> demande à Codex de te faire un review complet du papier en
> gardant qu'on vise derrière Talanta. Qu'est ce qu'il manque,
> les points faibles, ce qu'il faut faire pour que ca passe. Le
> tout dans un doc

Translation: produce a single document containing (1) a frank
gap analysis (what is missing), (2) the weak points (figures,
methodology, data, writing, claim strength), (3) a concrete
to-do list of what is needed for acceptance.

**The Talanta target is internal context** for shaping the
review — it does NOT mean you should re-introduce "Talanta"
wording into the paper itself (that rule remains in force). Your
review document is a working artifact under `paper_aom/review/`,
never cited from `main.tex` or `supplement.tex`.

## Inputs you must read

### Paper sources
- `paper_aom/main.tex` and `paper_aom/main.pdf`
- `paper_aom/supplement.tex` and `paper_aom/supplement.pdf`
- `paper_aom/references.bib`
- All files under `paper_aom/tables/` and `paper_aom/figures/`

### Working history (Codex previous iterations)
- `paper_aom/review/codex_report.md` (v1 → v7 update log)
- `paper_aom/review/codex_prompt_v4.md` through
  `paper_aom/review/codex_prompt_v7.md` (latest authoring rules)

### Data sources and stats
- `paper_aom/review/final_stats.md` and `v3_stats.md`
- `paper_aom/review/classification_stats.md` /
  `classification_stats_ext.md`
- `paper_aom/review/cohort_manifest.csv` and `cohort_manifest.md`
- `paper_aom/review/selector_diagnostics.csv` /
  `operator_frequency.csv` / `compact_bank_justification.md`
- `paper_aom/review/missing_datasets_per_variant.md`
- `paper_aom/review/failure_mode_table.csv`
- `paper_aom/review/results_inventory.md`
- `paper_aom/review/claim_ledger.md`

### Comparable journal-quality paper (style reference)
- `bench/tabpfn_paper/article/main.tex` — Robin's TabPFN paper,
  same cohort family, useful as a tone / level reference.

## What the review document must contain

Write a single markdown file at:
`paper_aom/review/talanta_review.md`

Structure it as a complete reviewer dossier with the following
top-level sections. Be specific, frank, and actionable.

### 1. Executive summary

Three to five paragraphs. State the paper's claim in one
sentence, the strongest piece of evidence, the weakest piece of
evidence, and the single most important thing to fix before
submission.

### 2. Talanta fit and scope

- Is the paper a fit for Talanta's scope (analytical chemistry,
  chemometrics, instrumentation) or does it skew too far toward
  generic ML? Be specific.
- What is the closest published Talanta precedent for the
  AOM-PLS / AOM-Ridge framing? Cite from `references.bib` or
  flag missing citations.
- What is the expected reviewer profile (chemometricians, NIRS
  practitioners, ML-oriented chemometricians) and what will each
  push back on?

### 3. Strengths

Bullet list, 5-10 items. Be specific: cite the figure, table,
section or paragraph. Distinguish methodological strengths
(maths, scope, protocol) from empirical strengths (sample size,
multi-seed, statistical tests).

### 4. Weaknesses, ranked by likelihood-of-being-cited-by-a-Talanta-reviewer

Each weakness gets:
- A short title.
- A two-to-three-sentence description.
- The exact place in the paper where the weakness manifests
  (`main.tex` line range or supplement section).
- A severity tag: **blocker**, **major**, **minor**.
- A recommended fix in one sentence.

Cover at minimum these axes:
- Cohort coverage and dataset count (current $N_{\cap}=32$ for
  the strict intersection; what reviewers will say; what to do).
- Cross-validation protocol (single train/test split per dataset
  vs the multi-seed claim; statistical-power critique).
- Comparator strength (is "default-cv5" PLS / Ridge an honest
  comparator, or do reviewers want SNV+SG+1stD as a stronger
  baseline?).
- Claim about "single fit", "auditability", "redeployment" —
  is each backed by a number or a concrete demonstration?
- AOM-Ridge headline single-seed vs multi-seed (the headline
  N=53 number is single-seed; reviewers will ask).
- Operator bank justification (is the "compact 9-operator bank"
  derivation transparent? `compact_bank_justification.md` is
  the reference; does the paper cite it adequately?).
- Repeatability and reproducibility (the user has not yet
  released `gbeurier/aom` and `gbeurier/pls4all`; both are
  announced but not live).
- Mathematical exposition (are Sections 4-5 self-contained?
  does an analytical chemist reader follow the derivations?).
- Classification claim (is the $N=13$ classification subset
  representative, or is it under-powered?).
- Failure modes (the paper does not currently dedicate space to
  cases where AOM loses; reviewers will ask).
- Figure quality / pedagogical clarity (each figure should tell
  one story; flag any that does not).

### 5. Missing experiments / data

Bullet list, each with:
- Description of the experiment to run.
- Expected effort (in core-hours and human-hours).
- Whether it is required for acceptance or merely strengthens
  the paper.
- Dependency on existing workspaces (which CSVs would feed it).

Consider at least:
- Filling the cartesian-HPO gap (the user's
  `missing_datasets_per_variant.md` lists the missing rows).
- Adding multi-seed (seeds 0/1/2) for AOM-Ridge headline.
- Adding a stronger conventional baseline (PLS + SNV + SG +
  1stD) to make the "complete preprocessing HPO" argument
  airtight.
- A small validation on an external split (instrument transfer,
  campaign change) to support the "redeployment" claim.
- Latency / inference-time numbers, not just fit/search-time.

### 6. Missing or weak literature citations

Audit `references.bib` against what a chemometrics-trained
reviewer expects to see in a paper on this topic. List any
missing reference category by:
- Topic.
- Two or three specific papers (author, year, journal, brief
  rationale).
- Where in the paper they would be cited.

Consider at least:
- Preprocessing canonical reviews beyond Rinnan 2009.
- Operator-adaptive PLS precedents (Cocchi / Ferrari /
  Engel / Lampérière etc., as relevant — verify before
  citing).
- POP-PLS or any prior "per-component operator" attempts.
- Sample selection (Kennard-Stone, SPXY, Stratified-SPXY).
- Compute-cost critiques of grid-search chemometrics.

### 7. Writing-level corrections

A short bullet list of writing issues that will be flagged in
copy-editing or by a careful reviewer:
- Unhelpful sentences or paragraphs (cite line numbers).
- Ambiguous notation.
- Caption-vs-body mismatches.
- Acronyms used without expansion on first use.
- Inconsistent variant naming (e.g. mixing CSV keys like
  `pls-tabpfn-hpo-25trials` with paper labels like `PLS-HPO`).
- French / English residues (the working language has
  bilingual fragments in some commit messages — verify the
  paper is fully English).

### 8. Figures and tables audit

Per figure (main + supplement) and per table:
- Caption claim vs body match.
- Information density (too sparse / too dense).
- Whether it would be the right figure for a Talanta reviewer to
  understand the contribution.
- A one-line suggested improvement, or "OK as-is".

### 9. Repository readiness

The user announces `gbeurier/aom` and `gbeurier/pls4all`. Audit:
- Is the announcement appropriate at submission, or does Talanta
  want code already live?
- What minimum content needs to be in `gbeurier/aom` at
  submission time (a reproducible run script, a Dockerfile, a
  small dataset for smoke-testing).
- `pls4all` is referenced as a multilanguage library
  (`/home/delete/nirs4all/pls4all`); do a quick `ls` and report
  what is there vs what would be expected at submission.

### 10. Recommended priorities for the next 1-2 weeks

A single ordered list (high to low priority) of work items.
Each item gets:
- One-line description.
- Expected impact on acceptance probability (high / medium /
  low).
- Effort estimate.
- Dependencies.

The user will pick items off this list. Be honest about which
items are "must-do" vs "nice-to-have".

### 11. Self-review caveats

Anything you noticed but did not have time to verify. Anything
you would re-check before submission.

## Hard constraints

- **READ-ONLY** on `paper_aom/main.tex`, `paper_aom/supplement.tex`,
  `paper_aom/references.bib`, `paper_aom/figures/*`, `paper_aom/tables/*`.
  Do not modify any of them.
- The only file you create is
  `paper_aom/review/talanta_review.md`.
- Do not re-run pdflatex or any data pipeline. This is a
  read + analyze pass.
- Do not include "Talanta" wording in any other file. The target
  journal is internal context for the review document only.
- Cite the paper's own line numbers when flagging a problem.
- Be specific: every weakness must come with a fix, every fix
  must come with effort estimate.
- Length target: 3,000-5,000 words. Long enough to be useful;
  short enough to be read in one sitting.
- Honest tone: it is more useful to flag a weak claim than to
  rubber-stamp it.

## Output

A single file `paper_aom/review/talanta_review.md`.

When done, report:
- Path to the file and its size.
- The three highest-impact items from the priority list (one
  sentence each).
- One sentence with your overall accept/reject leaning if the
  paper were submitted today, and your accept-after-revision
  leaning if the priority list is executed.
