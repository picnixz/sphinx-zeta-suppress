#!/usr/bin/env python3
# -*- coding: utf8 -*-

import os
import sys
import time

sys.path.insert(0, os.path.abspath('.'))

# General Sphinx options

extensions = ['sphinx.ext.intersphinx', 'sphinxcontrib.jquery', 'confval']
needs_sphinx = '6.2'

# Project configuration

project = 'sphinx-zeta-suppress'
# pylint: disable-next=C0209
project_copyright = '2023 - %s, picnix_, picnixz' % time.strftime('%Y')

root_doc = 'index'
source_suffix = '.rst'
exclude_patterns = ['_build']

# -----------------------------------------------------------------------------
# extension: sphinx.ext.intersphinx
# -----------------------------------------------------------------------------

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
    'docutils': ('https://sphinx-docutils.readthedocs.io/en/latest', None)
}
