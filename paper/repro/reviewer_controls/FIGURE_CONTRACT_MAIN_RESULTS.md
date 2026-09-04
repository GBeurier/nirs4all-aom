# Figure contract: revised claim-relevant effects

- **Conclusion:** regression effects remain the manuscript's claim-relevant results; under a newly matched PLS-DA protocol, the classification effect is centred at zero and is not evidence of an AOM advantage.
- **Evidence:** frozen regression summary rows plus the matched 13-task archived-headline PLS-DA intersection across three seeds (`matched_plsda/paired_summary.json`); the 14-task runnable set is a sensitivity only.
- **Comparison:** paired task-level median effects with percentile-bootstrap 95% intervals; the classification annotation also reports wins/ties/losses.
- **Export:** Python/Matplotlib vector PDF for the manuscript. The numerical values are reproduced in the manuscript table and in machine-readable CSV/JSON files, providing a non-visual text alternative.
- **Review risks:** do not reuse the archived unmatched +0.159 classification estimate; do not imply equivalence from an interval containing zero; preserve the distinction between RMSEP ratios and balanced-accuracy differences.
