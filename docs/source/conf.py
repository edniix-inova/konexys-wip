# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]  # repo/
sys.path.insert(0, str(ROOT / "src"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'KONEXYS'
author = 'Eduardo Perez Guzman - EDNIIX INOVA'
release = '0.1'
copyright = '2025, @edumaindev'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'myst_parser',
]  # 'markdown-it-py'
templates_path = ['_templates']
exclude_patterns = []
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

add_module_names = False
toc_object_entries_show_parents = 'hide'
# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# READ-THE-DOCS theme: https://github.com/readthedocs/sphinx_rtd_theme
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_logo = 'images/logo.png'
html_theme_options = {
    "sidebarwidth": "19em",
}

# -- Napoleon settings ------------------------------------------------
napoleon_google_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_preprocess_types = False
napoleon_use_param = False
napoleon_use_ivar = True

# -- MyST settings ----------------------------------------------------
# https://myst-parser.readthedocs.io/en/latest/configuration.html
myst_enable_extensions = [
    "html_image",
]