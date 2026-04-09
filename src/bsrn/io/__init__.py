"""
I/O subpackage: BSRN file readers, FTP retrieval, and auxiliary radiation sources.

Modules expose readers (:mod:`reader`), FTP helpers (:mod:`retrieval`), CAMS CRS /
McClear / MERRA-2 / NSRDB integrations, and thin Hugging Face fetch paths.
"""

from . import crs, reader, retrieval, mcclear, merra2, nsrdb
