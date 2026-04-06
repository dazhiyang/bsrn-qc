Tutorials
=========

This section provides step-by-step tutorials for using `bsrn` for various tasks.
These tutorials are provided as interactive Jupyter notebooks.

**1.data_downloading** — BSRN FTP credentials, browse station file inventory with
:func:`~bsrn.io.retrieval.get_bsrn_file_inventory`, and download station-to-archive
``.dat.gz`` files with :func:`~bsrn.io.retrieval.download_bsrn_stn`.

**2.quality_control** — QIQ **March** LR0100 month: **Part A** runs
:meth:`~bsrn.dataset.BSRNDataset.qc_test` and tallies **tier row counts** from ``flag*``
columns; **Part B** exercises individual ``*_test`` helpers (PPL, ERL, closure, diffuse
*k*, *k*-indices, tracker-off), and **§7** checks that Part A and Part B agree per tier
(using :func:`~bsrn.qc.wrapper.run_qc`). **§8** is the **daily QC audit table**
(``ds.plot.table``); **§9** is a **faceted day** plot (``ds.plot.daily``) before
masking; **§10** applies :meth:`~bsrn.dataset.BSRNDataset.qc_mask` and **replots** the
audit table on the masked minute series.

**3.time_averaging** — explicit time aggregation with
:func:`~bsrn.utils.averaging.pretty_average` (**floor** / **ceiling** / **center**,
``match_ceiling_labels``, samples per interval).

**4.clear_sky_detection** — McClear-based clear-sky columns, QC, Reno clear-sky
detection via :func:`~bsrn.utils.clear_sky_detection.detect_clearsky`, and CSD-point
visualization (QIQ September example).

**5.cloud_enhancement_event** — REST2 clear-sky (MERRA-2 via Hugging Face), QC
(closure, diffuse ratio, tracker-off), and Killinger/Yang/Gueymard cloud enhancement detection with
:func:`~bsrn.utils.cee_detection.detect_cee`.

.. toctree::
   :maxdepth: 1
   :caption: Core Workflows

   1.data_downloading
   2.quality_control
   3.time_averaging
   4.clear_sky_detection
   5.cloud_enhancement_event
