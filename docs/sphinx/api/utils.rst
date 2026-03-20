Utilities
=========

Explicit time averaging
-----------------------
:func:`~bsrn.utils.averaging.pretty_average` builds **floor**, **ceiling**, or **center** windows on a
:class:`~pandas.DatetimeIndex`. It is **not** :meth:`pandas.DataFrame.resample`.

Semantics (month-edge label trimming, coverage thresholds, ``match_ceiling_labels`` for **center**)
and notebook examples (QIQ, ``hourly_sample_counts``) are documented in
:doc:`../tutorials/2.qc_and_averaging`.

.. autosummary::
   :toctree: generated/

   bsrn.utils.averaging.pretty_average

QC Statistics
-------------
.. autosummary::
   :toctree: generated/

   bsrn.utils.quality.get_daily_stats

Clear-sky Detection (CSD)
-------------------------
.. autosummary::
   :toctree: generated/

   bsrn.utils.clear_sky_detection.reno_csd
   bsrn.utils.clear_sky_detection.ineichen_csd
   bsrn.utils.clear_sky_detection.lefevre_csd
   bsrn.utils.clear_sky_detection.brightsun_csd
   bsrn.utils.clear_sky_detection.detect_clearsky

Cloud Enhancement (CEE)
-----------------------
.. autosummary::
   :toctree: generated/

   bsrn.utils.cee_detection.detect_cee
   bsrn.utils.cee_detection.killinger_ced
   bsrn.utils.cee_detection.gueymard_ced
   bsrn.utils.cee_detection.wang_ced

Calculations
------------
.. autosummary::
   :toctree: generated/

   bsrn.utils.calculations.calc_kb
   bsrn.utils.calculations.calc_kd
   bsrn.utils.calculations.calc_kt
