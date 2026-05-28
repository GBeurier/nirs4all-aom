\name{aom_pls_tune}
\alias{aom_pls_tune}
\title{Outer-K-fold grid HPO for aom_pls}
\description{
For each (max_components, preproc) combination, fits \code{\link{aom_pls}}
on each outer-train fold and evaluates RMSE on the outer-test fold.
Returns the best config and a model refit on the full data.
}
\usage{
aom_pls_tune(X, y,
             max_components_grid = c(5L, 10L, 15L, 20L, 25L),
             preproc_grid = c("none", "snv", "osc", "asls", "asls+osc"),
             n_folds = 5L,
             cv_mode = "kfold",
             outer_folds = 5L,
             one_se_rule = FALSE,
             random_state = 0L)
}
\arguments{
\item{X}{Numeric matrix (n_samples, n_features).}
\item{y}{Numeric vector (n_samples).}
\item{max_components_grid}{Integer vector of candidate max_components.}
\item{preproc_grid}{Character vector of candidate preprocessing strings.}
\item{n_folds}{Inner CV folds passed to \code{\link{aom_pls}}.}
\item{cv_mode}{Inner CV strategy passed to \code{\link{aom_pls}}.}
\item{outer_folds}{Outer CV folds used to score each candidate config.}
\item{one_se_rule}{Apply the one-standard-error rule inside \code{aom_pls}.}
\item{random_state}{Seed for the outer K-fold shuffler.}
}
\value{
A list with \code{best_params} (named list with max_components and preproc),
\code{best_score} (mean outer RMSE), \code{all_results} (data frame of all
candidate scores), and \code{refit_model} (an \code{aom_pls} fitted on the
full data with the best config).
}
\seealso{\code{\link{aom_pls}}}
