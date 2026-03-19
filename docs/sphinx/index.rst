.. bsrn documentation master file

.. raw:: html

   <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
     <img src="_static/logo.jpg" alt="bsrn" style="height: 48px; width: auto;">
     <h1 style="margin: 0;">bsrn</h1>
   </div>

**bsrn** is a Python package for the `Baseline Surface Radiation Network (BSRN) <https://bsrn.awi.de/>`_.
It provides automated quality control (QC), solar geometry, clear-sky modeling, clear-sky detection (CSD),
cloud enhancement event (CEE) detection, irradiance separation, data retrieval, and visualization tools
for BSRN station-to-archive files.

Overview
--------

The package implements a six-level QC pipeline based on the BSRN Operations Manual and Forstinger et al. (2021).
It supports three clear-sky models (Ineichen, McClear, REST2), multiple CSD and CEE detection methods,
and irradiance decomposition models. MERRA-2 atmospheric inputs for REST2 are fetched from Hugging Face
into RAM with no disk cache.

Installation
------------

From PyPI (stable release):

.. code-block:: bash

   pip install bsrn

From GitHub (latest development version):

.. code-block:: bash

   pip install git+https://github.com/dazhiyang/bsrn.git

For visualization features (plotnine, matplotlib):

.. code-block:: bash

   pip install bsrn[viz]

Quick Start
-----------

.. code-block:: python

   from bsrn.io.readers import read_station_to_archive
   from bsrn.modeling.clear_sky import add_clearsky_columns

   # Read a BSRN station-to-archive file
   df = read_station_to_archive("data/QIQ/qiq0124.dat.gz", logical_records="lr0100")

   # Add clear-sky columns (REST2 fetches MERRA-2 from Hugging Face automatically)
   df = add_clearsky_columns(df, station_code="QIQ", model="rest2")

Features
--------

**Quality control (6 levels)**

* Level 1 (PPL): Physically possible limits for :math:`G_h`, :math:`B_n`, :math:`D_h`, :math:`L_d`
* Level 2 (ERL): Extremely rare climatological limits
* Level 3 (Closure): :math:`G_h` vs :math:`B_n \cos Z + D_h` consistency checks
* Level 4 (Diffuse ratio): :math:`k`–:math:`k_t` and diffuse-fraction checks
* Level 5 (K-indices): Clearness-index and :math:`k_b`/:math:`k_t` tests
* Level 6 (Tracker): Solar tracker off detection

**Clear-sky models**

* Ineichen (monthly Linke turbidity)
* McClear (CAMS SoDa API, from 2004 onward)
* REST2 (MERRA-2 from Hugging Face)

**Clear-sky detection**

Reno, Ineichen, Lefevre, BrightSun

**Cloud enhancement event (CEE) detection**

Killinger, Gueymard-style, Wang

**Irradiance separation**

Erbs, BRL, Engerer2, Yang4

Tutorials
---------

Jupyter notebooks demonstrating key workflows:

* `Clear Sky Detection Demo With McClear <https://github.com/dazhiyang/bsrn/blob/main/docs/tutorials/clear_sky_detection.ipynb>`_
  — McClear clear-sky modeling, QC, Reno CSD, and CSD-point visualization

* `Cloud Enhancement Event Detection with REST2 <https://github.com/dazhiyang/bsrn/blob/main/docs/tutorials/cloud_enhancement_event.ipynb>`_
  — REST2 clear-sky, QC (closure, diffuse ratio, tracker-off), Wang CEE detection

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Links
-----

* `GitHub repository <https://github.com/dazhiyang/bsrn>`_
* `BSRN MERRA-2 dataset (Hugging Face) <https://huggingface.co/datasets/dazhiyang/bsrn-merra2>`_
* `BSRN website <https://bsrn.awi.de/>`_

For detailed API documentation, see the :ref:`modindex`.
