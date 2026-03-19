# Configuration file for the Sphinx documentation builder.
# See https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add project root to path so autodoc can import bsrn (Read the Docs runs from repo root)
sys.path.insert(0, os.path.abspath('../../src'))
sys.path.insert(0, os.path.abspath('../../'))

project = "bsrn"
copyright = "Dazhi Yang"
author = "Dazhi Yang"
release = "0.1.2"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
]

templates_path = ["_templates"]
exclude_patterns = []

# Cross-reference other projects' docs
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
}

# Shortcuts for GitHub links (e.g. :issue:`123`, :pull:`45`, :ghuser:`dazhiyang`)
extlinks = {
    "issue": ("https://github.com/dazhiyang/bsrn/issues/%s", "GH%s"),
    "pull": ("https://github.com/dazhiyang/bsrn/pull/%s", "GH%s"),
    "ghuser": ("https://github.com/%s", "@%s"),
}

autosummary_generate = True

# HTML theme
# Change this line:
html_theme = 'pydata_sphinx_theme'
# Optional: Add this block to add a GitHub link to the top right of your site
html_theme_options = {
    "github_url": "https://github.com/dazhiyang/bsrn",
    "show_nav_level": 2,
}
html_static_path = ["_static"]
html_logo = "_static/logo.jpg"
