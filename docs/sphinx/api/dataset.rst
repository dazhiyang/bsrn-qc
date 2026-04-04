BSRNDataset
===========

The central data object for one monthly BSRN station file.
``BSRNDataset`` wraps station identity, validated Pydantic logical
records (``LR0100``, ``LR0300``, ``LR4000``), and auto-resolved
metadata into a single typed model.

Pipeline methods delegate to the existing standalone functions so
both the object-oriented and functional APIs remain available.

.. autosummary::
   :toctree: generated/

   bsrn.dataset.BSRNDataset

Construction
------------

.. autosummary::
   :toctree: generated/

   bsrn.dataset.BSRNDataset.from_file

Properties
----------

.. autosummary::
   :toctree: generated/

   bsrn.dataset.BSRNDataset.data

Pipeline Methods
----------------

.. autosummary::
   :toctree: generated/

   bsrn.dataset.BSRNDataset.add_solpos
   bsrn.dataset.BSRNDataset.add_clearsky
   bsrn.dataset.BSRNDataset.run_qc
