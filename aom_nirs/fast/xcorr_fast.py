"""Compatibility API for the operator optimization now enabled by default.

The canonical implementation is in ``aom_nirs.pls.operators`` and is shared
by PLS, Ridge, Gaussian operators and FastAOM. Historical install/uninstall
calls retain their bookkeeping API but no longer mutate global numerical
functions. There is one implementation and one padding convention.
"""

from __future__ import annotations

from aom_nirs.pls.operators import _xcorr_zero_pad as xcorr_zero_pad_fast

__all__ = [
    "install_xcorr_patch",
    "is_patch_installed",
    "uninstall_xcorr_patch",
    "xcorr_zero_pad_fast",
]

_PATCH_REQUESTED = False


def install_xcorr_patch() -> None:
    """Compatibility no-op: optimized operators are always active."""
    global _PATCH_REQUESTED
    _PATCH_REQUESTED = True


def uninstall_xcorr_patch() -> None:
    """Clear historical patch bookkeeping; optimized operators remain active."""
    global _PATCH_REQUESTED
    _PATCH_REQUESTED = False


def is_patch_installed() -> bool:
    """Whether a legacy caller requested the now-unnecessary patch."""
    return _PATCH_REQUESTED
