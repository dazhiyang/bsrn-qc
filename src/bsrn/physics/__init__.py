"""
Physics subpackage: solar geometry and related helpers (public API in ``geometry``).

Internal SPA routines live in :mod:`bsrn.physics.spa` and are used by
:mod:`bsrn.physics.geometry`; do not import :mod:`spa` from application code.
"""

from . import geometry
