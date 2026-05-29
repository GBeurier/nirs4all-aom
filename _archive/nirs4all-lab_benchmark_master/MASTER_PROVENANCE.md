# Master CSV provenance / reconciliation

**File:** `benchmark_master_results.csv` (this directory).

## The discrepancy
The master is an **append-growing build**: each ingest adds rows and re-hashes, logged in
`nirs4all-lab/benchmark/results/MASTER_CSV_HASH.txt`. That ledger's **last recorded freeze** is:

```
2026-05-10 16:35 CEST   data_rows = 24,879   sha256 = 000eb68c5371b41618d64c3b2765022e34502abfa578ad71fd36ee0ce7484ab5
```

The file **actually on disk here** is a *later, unlogged* build:

```
on disk (2026-05-29)    data_rows = 35,930   sha256 = 7ddbcd240628c6ac6197e4012f1248c7d8b423b7365aa8613ba8da2b0c7ea910   bytes = 30,043,682
```

i.e. ~**+11,051 rows beyond the last logged freeze** (later router / AOM-Ridge ingests that were never
written back to the hash ledger). Both are "the master" — the on-disk one is simply newer and
undocumented. This is a *provenance/bookkeeping* gap, not a data error.

## Why it barely matters for the paper
The paper's **headline numbers do not come from the master.** PLS/Ridge ratios, wins, p-values,
runtimes and classification come from the curated paper run-dirs (`benchmarks/runs/...`) via
`paper/review/final_stats.md` and `paper/repro/*.py`. The master is read by **only one** analysis —
the transfer + latency table (`paper/repro/transfer_latency.py`, the Rd25 leave-site-out result) —
and those values were cross-checked against `benchmarks/runs/ridge/all54_headline/results.csv` to full
precision. So the reconciliation risk is contained to the B1 transfer/latency numbers.

## Reconciliation (pick one before camera-ready)
1. **Freeze the current build (recommended, minutes).** Append a new entry to
   `MASTER_CSV_HASH.txt` recording `data_rows=35,930`, `sha256=7ddbcd24…`, date, and the ingest trigger
   (which runs were added since the 24,879 freeze). Cite that sha as the master version of record.
2. **Rebuild deterministically.** Re-run the master aggregator from the canonical run-dirs so the
   35,930-row build is reproducible from committed CSVs, then freeze its hash.
3. **Pin per-analysis (minimum).** State in `transfer_latency.py` (already does) and the paper that the
   transfer/latency numbers were read from this exact file (sha `7ddbcd24…`); since they match
   `all54_headline`, no master freeze is strictly required for the paper, only for the dataset release.

The author decides #1 vs #2 at release; #3 already holds for the manuscript.
