# cran-comments.md

## v0.1.0 — initial CRAN submission

### Test environments

- Local: Ubuntu 22.04, R 4.4.3 (via conda r-base)
- GitHub Actions:
  - ubuntu-latest, R release
  - macos-latest, R release
  - windows-latest, R release
- R-hub (`rhub::check_for_cran()`):
  - Windows Server 2022, R-devel, 64 bit
  - Ubuntu Linux 20.04.1 LTS, R-release, GCC
  - Fedora Linux, R-devel, clang, gfortran

### R CMD check results

0 errors | 0 warnings | 1 note (new submission)

### Notes for the CRAN reviewer

- This is a new release. The package bundles a header-only C++17
  re-implementation of the AOM-PLS algorithm published in the upstream
  `nirs4all` repository (CeCILL-2.1) — re-implemented from scratch as a
  standalone library without a runtime dependency on `nirs4all`.
- The `inst/include/` directory contains:
  - Our header-only C++ library (~50 KB).
  - A vendored copy of Eigen 3.4 (MPL-2.0), required for the C++ template
    metaprogramming used by the SIMPLS implementation. The MPL-2.0 is
    compatible with CeCILL-2.1 and the license is documented in `LICENSE`.
- All Rcpp wrappers are deterministic and bounded; no network access, no
  writes outside the session's tempdir.
- The package uses `LinkingTo: Rcpp` and pre-generated `RcppExports.{R,cpp}`
  files (built via `Rcpp::compileAttributes()`).

### Reverse dependencies

None at this time (initial submission).
