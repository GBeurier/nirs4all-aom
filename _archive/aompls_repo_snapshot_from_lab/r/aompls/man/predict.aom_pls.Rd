\name{predict.aom_pls}
\alias{predict.aom_pls}
\alias{coef.aom_pls}
\alias{print.aom_pls}
\alias{summary.aom_pls}
\title{Methods for the aom_pls class}
\description{
S3 methods for fitted \code{\link{aom_pls}} models.
\code{predict()} returns predicted y values for new spectra.
\code{coef()} returns the regression coefficient vector.
\code{print()} prints a brief summary.
\code{summary()} prints the RMSE curve of the selected operator.
}
\usage{
\method{predict}{aom_pls}(object, newdata, ...)
\method{coef}{aom_pls}(object, ...)
\method{print}{aom_pls}(x, ...)
\method{summary}{aom_pls}(object, ...)
}
\arguments{
\item{object, x}{An \code{aom_pls} object returned by \code{\link{aom_pls}}.}
\item{newdata}{Numeric matrix with the same number of columns as the
  training matrix.}
\item{...}{Additional arguments (unused; required by the S3 generic).}
}
\value{
\code{predict()} returns a numeric vector of length \code{nrow(newdata)}.
\code{coef()} returns a numeric vector of length \code{n_features}.
\code{print()} and \code{summary()} are called for their side effect and
invisibly return the input object.
}
\seealso{\code{\link{aom_pls}}}
