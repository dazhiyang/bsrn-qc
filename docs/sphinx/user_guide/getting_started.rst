Getting Started
===============

This guide provides a quick introduction to using `bsrn` for quality control and clear-sky modeling.

BSRNDataset (recommended)
-------------------------

The simplest way to work with a BSRN archive file is through
:class:`~bsrn.dataset.BSRNDataset`, which reads the file, resolves
station metadata, and exposes chainable pipeline methods:

.. code-block:: python

   import bsrn

   ds = bsrn.BSRNDataset.from_file("data/QIQ/qiq0125.dat.gz")

   ds.solpos()            # solar position + extraterrestrial
   ds.clear_sky()         # clear-sky irradiance (Ineichen)
   ds.qc_test()           # 6-level quality control flags
   ds.qc_mask()           # optional: NaN failed irradiance, drop flags

Logical Record Selection
------------------------

You can select which logical records are parsed using ``include_lrs``.
Current selectors are ``"lr0100"``, ``"lr0300"``, and ``"lr4000"``.

.. code-block:: python

   import bsrn

   ds = bsrn.BSRNDataset.from_file(
       "data/QIQ/qiq0125.dat.gz",
       include_lrs=["lr0100", "lr0300"],
       strict=False,
   )

   # Query loaded logical records.
   lr0100 = ds.get_lr("lr0100")
   has_lr0300 = ds.has_lr("lr0300")

When to use each LR access pattern:

.. code-block:: python

   from bsrn.archive import LR0100

   # Use LR0100.from_file(...) when you only need one LR object directly.
   lr0100_direct = LR0100.from_file("data/QIQ/qiq0125.dat.gz")

   # Use ds.get_lr(...) when you already work with a dataset pipeline object.
   ds = bsrn.BSRNDataset.from_file("data/QIQ/qiq0125.dat.gz")
   lr0100_from_ds = ds.get_lr("lr0100")

Both patterns are valid. Pick one based on workflow context; there is no
need to use both in the same script unless you explicitly want both views.

Functional API
--------------

All pipeline steps are also available as standalone functions,
useful when working with non-BSRN data or custom DataFrames:

.. code-block:: python

   from bsrn.physics.geometry import add_solpos_columns
   from bsrn.modeling.clear_sky import add_clearsky_columns
   from bsrn.qc.wrapper import run_qc

   df = add_solpos_columns(df, lat=47.80, lon=124.49, elev=170)
   df = add_clearsky_columns(df, lat=47.80, lon=124.49, elev=170)
   df = run_qc(df, lat=47.80, lon=124.49, elev=170)

Key Features
------------

- **Automated Quality Control**: 6 levels of QC based on BSRN standards.
- **Clear-sky Modeling**: Support for Ineichen, McClear, and REST2.
- **Clear-sky Detection**: Multiple algorithms (Reno, Ineichen, etc.).
- **Cloud Enhancement detection**: Killinger, Yang, Gueymard.
- **Irradiance Separation**: Erbs, BRL, Engerer2, Yang4.
