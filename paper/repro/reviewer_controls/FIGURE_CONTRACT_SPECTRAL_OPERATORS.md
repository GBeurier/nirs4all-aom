Core conclusion: The compact AOM bank applies chemically familiar, fixed linear views of the same NIR spectra: smoothing suppresses high-frequency variation, differentiation emphasizes local band shape, and detrending removes broad additive/linear backgrounds without creating a separate deployed pipeline.

Figure archetype: quantitative grid.

Target journal/output: Talanta; editable SVG and PDF, 600-dpi TIFF, 183 mm width.

Backend: Python only.

Final size: 183 x 103 mm.

Panel map:

- a: raw reflectance spectra from the ALPINE phosphorus calibration task.
- b: the same spectra after SG smoothing (window 21, polynomial order 3).
- c: the same spectra after first-derivative SG (window 21, polynomial order 3).
- d: the same spectra after degree-1 polynomial detrending.

Evidence hierarchy:

- Hero evidence: raw spectra and their between-sample envelope.
- Validation evidence: three exact compact-bank transforms applied to the same observations.
- Controls/robustness: identical wavelength range, sample set and quantile summary in every panel; source data exported as CSV.

Statistics needed: no inferential statistics; lines are group medians and bands are the 10th--90th percentiles. Group and total sample counts are reported.

Source data needed: ALPINE_P_291_KS training spectra and origin metadata; transformed median and quantile curves exported in tidy CSV form.

Image-integrity notes: vector line plot; no local image manipulation; no interpolation; transformations use the production AOM operator implementations. Only the displayed wavelength interval is cropped after transformation to avoid emphasizing zero-padding boundaries.

Reviewer risk: the figure is illustrative rather than evidence of predictive superiority. Its caption must not attribute individual absorption bands without a dedicated assignment analysis.
