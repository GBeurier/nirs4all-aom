# AOM-Ridge headline seed audit

Source workspaces: `da001_audit20_seeds012, da001_partial_fast12_seeds012`.
Audit datasets (union): 26.  N_cap (main text): 32.  Overlap used for the summary: 18.

Cross-workspace agreement on duplicated (dataset, variant, seed) triples: 36 triples checked, max |Δrmsep| = 0.000e+00 (tolerance 1e-08).

## Per-variant summary on the audit-overlap subset

| Variant | Audit datasets | Seeds 0/1/2 complete | Max RMSEP span | Median RMSEP span | Datasets with non-zero span |
|---|---:|---:|---:|---:|---:|
| AOMRidge-AutoSelect | 18 | 18 | 0 | 0 | 0 |
| AOMRidge-Blender | 18 | 18 | 0 | 0 | 0 |

## Per-dataset values on the audit-overlap subset

RMSEP at seeds 0 / 1 / 2 for the two headline variants on the datasets where the audit workspaces overlap with N_cap.

| Dataset | Variant | seed 0 | seed 1 | seed 2 |
|---|---|---:|---:|---:|
| ALPINE_P_291_KS | AOMRidge-AutoSelect | 0.0570384 | 0.0570384 | 0.0570384 |
| ALPINE_P_291_KS | AOMRidge-Blender | 0.0567969 | 0.0567969 | 0.0567969 |
| An_spxyG70_30_byCultivar_MicroNIR_NeoSpectra | AOMRidge-AutoSelect | 3.86187 | 3.86187 | 3.86187 |
| An_spxyG70_30_byCultivar_MicroNIR_NeoSpectra | AOMRidge-Blender | 3.83837 | 3.83837 | 3.83837 |
| Beer_OriginalExtract_60_KS | AOMRidge-AutoSelect | 0.155666 | 0.155666 | 0.155666 |
| Beer_OriginalExtract_60_KS | AOMRidge-Blender | 0.202781 | 0.202781 | 0.202781 |
| Beer_OriginalExtract_60_YbaseSplit | AOMRidge-AutoSelect | 0.273632 | 0.273632 | 0.273632 |
| Beer_OriginalExtract_60_YbaseSplit | AOMRidge-Blender | 0.271584 | 0.271584 | 0.271584 |
| Biscuit_Sucrose_40_RandomSplit | AOMRidge-AutoSelect | 1.26684 | 1.26684 | 1.26684 |
| Biscuit_Sucrose_40_RandomSplit | AOMRidge-Blender | 1.20666 | 1.20666 | 1.20666 |
| C_woOutlier | AOMRidge-AutoSelect | 1.89866 | 1.89866 | 1.89866 |
| C_woOutlier | AOMRidge-Blender | 1.87391 | 1.87391 | 1.87391 |
| Ccar_spxyG_block2deg | AOMRidge-AutoSelect | 73.9245 | 73.9245 | 73.9245 |
| Ccar_spxyG_block2deg | AOMRidge-Blender | 51.5339 | 51.5339 | 51.5339 |
| Corn_Oil_80_ZhengChenPelegYbaseSplit | AOMRidge-AutoSelect | 0.0174273 | 0.0174273 | 0.0174273 |
| Corn_Oil_80_ZhengChenPelegYbaseSplit | AOMRidge-Blender | 0.0193105 | 0.0193105 | 0.0193105 |
| DIESEL_bp50_246_b-a | AOMRidge-AutoSelect | 2.8246 | 2.8246 | 2.8246 |
| DIESEL_bp50_246_b-a | AOMRidge-Blender | 3.01483 | 3.01483 | 3.01483 |
| DIESEL_bp50_246_hlb-a | AOMRidge-AutoSelect | 2.86586 | 2.86586 | 2.86586 |
| DIESEL_bp50_246_hlb-a | AOMRidge-Blender | 2.79811 | 2.79811 | 2.79811 |
| Fv_Fm_grp70_30 | AOMRidge-AutoSelect | 0.0310635 | 0.0310635 | 0.0310635 |
| Fv_Fm_grp70_30 | AOMRidge-Blender | 0.0306448 | 0.0306448 | 0.0306448 |
| N_woOutlier | AOMRidge-AutoSelect | 0.223855 | 0.223855 | 0.223855 |
| N_woOutlier | AOMRidge-Blender | 0.224291 | 0.224291 | 0.224291 |
| Rd25_GTtestSite | AOMRidge-AutoSelect | 0.192192 | 0.192192 | 0.192192 |
| Rd25_GTtestSite | AOMRidge-Blender | 0.218554 | 0.218554 | 0.218554 |
| Rice_Amylose_313_YbasedSplit | AOMRidge-AutoSelect | 2.00734 | 2.00734 | 2.00734 |
| Rice_Amylose_313_YbasedSplit | AOMRidge-Blender | 2.04992 | 2.04992 | 2.04992 |
| TIC_spxy70 | AOMRidge-AutoSelect | 3.32584 | 3.32584 | 3.32584 |
| TIC_spxy70 | AOMRidge-Blender | 3.39562 | 3.39562 | 3.39562 |
| WUEinst_spxyG70_30_byCultivar_MicroNIR_NeoSpectra | AOMRidge-AutoSelect | 1.48243 | 1.48243 | 1.48243 |
| WUEinst_spxyG70_30_byCultivar_MicroNIR_NeoSpectra | AOMRidge-Blender | 1.44617 | 1.44617 | 1.44617 |
| brix_groupSampleID_stratDateVar_balRows | AOMRidge-AutoSelect | 3.59104 | 3.59104 | 3.59104 |
| brix_groupSampleID_stratDateVar_balRows | AOMRidge-Blender | 3.76058 | 3.76058 | 3.76058 |
| ph_groupSampleID_stratDateVar_balRows | AOMRidge-AutoSelect | 0.306149 | 0.306149 | 0.306149 |
| ph_groupSampleID_stratDateVar_balRows | AOMRidge-Blender | 0.2979 | 0.2979 | 0.2979 |
