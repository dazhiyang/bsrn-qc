Tutorials
=========

This section provides step-by-step tutorials for using `bsrn` for various tasks.
These tutorials are provided as interactive Jupyter notebooks.

**1.data_downloading** — BSRN FTP credentials; list files with
:func:`~bsrn.io.retrieval.get_bsrn_file_inventory`; optional FTP coverage heatmap via
:func:`~bsrn.visualization.availability.plot_bsrn_availability`; download archives by
filename with :func:`~bsrn.io.retrieval.download_bsrn_files` (other helpers such as
:func:`~bsrn.io.retrieval.download_bsrn_stn` are also available).

:doc:`1.data_downloading`

**2.quality_control** — QIQ **March** LR0100 month: :meth:`~bsrn.dataset.BSRNDataset.solpos`
and :meth:`~bsrn.dataset.BSRNDataset.clear_sky` (REST2 example), then **Part A**
:meth:`~bsrn.dataset.BSRNDataset.qc_test`, which delegates to
:func:`~bsrn.qc.wrapper.run_qc` and adds ``flag*`` columns for **tier row counts**;
**Part B** calls the same tests via individual low-level helpers (PPL, ERL, closure,
diffuse ratio, *k* / *k*-indices, tracker). **§7** checks that Part A and Part B agree
per tier. **§8** is the daily QC audit table (``plot.table()`` on :attr:`~bsrn.dataset.BSRNDataset.plot`);
**§9** is a faceted day plot (``plot.daily(...)``) before masking;
**§10** applies :meth:`~bsrn.dataset.BSRNDataset.qc_mask` and refreshes the audit table on the
masked series.

:doc:`2.quality_control`

**3.to_archive** — Station-to-archive **writing**: `bsrn.archive` logical records and
:meth:`~bsrn.archive.LR0001.get_bsrn_format`, rBSRN-style minute columns (``year_month``, ``rep(1, n)``
via ``pd.Series([1] * n)`` for demo GHI/DHI, other LR0100 fields missing), ``LR4000`` + ``LR4000CONST``
in LR0003; comments show how to name output files in a real script; preview printed only (notebook
pre-rendered for Sphinx).

:doc:`3.to_archive`

**4.time_averaging** — Same preprocessing pipeline as tutorial 2 on QIQ **August** data,
then :meth:`~bsrn.dataset.BSRNDataset.average` on a dataset copy and detailed use of
:func:`~bsrn.utils.averaging.pretty_average` (**floor** / **ceiling** / **center**,
``match_ceiling_labels``, samples per interval).

:doc:`4.time_averaging`

**5.clear_sky_detection** — McClear clear-sky columns via
:func:`~bsrn.modeling.clear_sky.add_clearsky_columns`, QC, Reno clear-sky screening with
:func:`~bsrn.utils.reno_csd`, and matplotlib plots of GHI vs clear-sky with Reno masks
(QIQ September example). Other CSD algorithms are available through
:func:`~bsrn.utils.clear_sky_detection.detect_clearsky`.

:doc:`5.clear_sky_detection`

**6.cloud_enhancement_event** — REST2 clear-sky (:meth:`~bsrn.dataset.BSRNDataset.clear_sky`
with MERRA-2 via Hugging Face), QC (closure, diffuse ratio, tracker-off), and cloud
enhancement events via :func:`~bsrn.utils.cee_detection.detect_cee` (methods
``killinger``, ``yang``, ``gueymard``).

:doc:`6.cloud_enhancement_event`

**7.separation_modeling** — QIQ **2024** full year: concatenate twelve monthly archives,
:func:`~bsrn.qc.wrapper.run_qc`, REST2 clear-sky via
:func:`~bsrn.modeling.clear_sky.add_clearsky_columns`, then Erbs, BRL, Engerer2, and Yang4
irradiance separation and :func:`~bsrn.visualization.separation.plot_k_vs_kt` (**k** vs **k_t**).

:doc:`7.separation_modeling`
