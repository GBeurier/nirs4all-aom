\name{aom_pls}
\alias{aom_pls}
\title{Fit AOM-PLS (compact, PLS1)}
\description{
Adaptive Operator Mixture Partial Least Squares regression (PLS1) with a
9-operator compact bank (Identity, Savitzky-Golay smoothing and derivatives,
polynomial detrend, finite difference). Cross-validates each operator over
prefix lengths k = 1..max_components and picks the (operator, k) pair
minimising mean fold RMSE.
}
\usage{
aom_pls(X, y,
        max_components = 15L,
        n_folds = 5L,
        cv_mode = c("kfold", "spxy", "holdout", "external"),
        one_se_rule = FALSE,
        random_state = 0L,
        preproc = c("none", "snv", "msc", "osc", "asls", "snv+osc", "asls+osc"),
        osc_n_components = 1L,
        asls = list(lam = 1e5, p = 0.01, n_iter = 10L),
        center = TRUE,
        external_folds = NULL)
}
\arguments{
\item{X}{Numeric matrix of shape (n_samples, n_features).}
\item{y}{Numeric vector of length n_samples (univariate response).}
\item{max_components}{Maximum number of PLS components to extract.}
\item{n_folds}{Number of CV folds. Ignored when \code{cv_mode = "external"}.}
\item{cv_mode}{Cross-validation strategy: \code{"kfold"} (own RNG),
  \code{"spxy"}, \code{"holdout"}, or \code{"external"}.}
\item{one_se_rule}{Apply the one-standard-error parsimony rule.}
\item{random_state}{Integer seed for the internal CV shuffler (own RNG;
  not bit-compatible with numpy's MT19937).}
\item{preproc}{One-shot preprocessing applied before AOM. One of
  \code{"none"}, \code{"snv"}, \code{"msc"}, \code{"osc"}, \code{"asls"},
  \code{"snv+osc"}, \code{"asls+osc"}.}
\item{osc_n_components}{Number of OSC components (used when preproc
  includes "osc").}
\item{asls}{Named list with \code{lam}, \code{p}, \code{n_iter} controlling
  the asymmetric least squares baseline correction.}
\item{center}{Mean-center X and y before AOM. Strongly recommended.}
\item{external_folds}{List of integer vectors of TEST indices per fold.
  Required when \code{cv_mode = "external"}. Indices are 0-based.}
}
\value{
An object of class \code{"aom_pls"} (a list) containing the fitted
coefficients, intercept, selected operator name and index, n_components,
RMSE curves, and fold indices used.
}
\examples{
\donttest{
set.seed(0)
X <- matrix(rnorm(200 * 50), 200, 50)
X[, 10] <- X[, 10] + seq_len(200) * 0.05
y <- seq_len(200) * 0.05 + rnorm(200) * 0.01
m <- aom_pls(X, y, max_components = 5L)
pred <- predict(m, X)
print(m)
}
}
\seealso{\code{\link{predict.aom_pls}}, \code{\link{aom_pls_tune}}}
