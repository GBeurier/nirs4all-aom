# Reviewer controls

Read-only aggregation controls prepared for the targeted Talanta revision. The
script reads frozen benchmark artifacts, performs no fits, and never writes to
the canonical manuscript or its table directory.

Run from any directory:

```bash
bash paper/repro/reviewer_controls/run.sh
```

The wrapper pins the process to logical CPUs 10--13, fixes all common
numerical-library thread pools to one thread, and hides GPUs. Outputs are deterministic CSV files and
`REPORT.md` in this directory.
