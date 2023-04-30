This extension serves in suppressing logging records issued by a Sphinx logger.

The records are filtered according to their context (logger name and record
level) and their formatted message.

Usage
=====

Recall that Sphinx automatically adds a ``sphinx.`` prerfix to the logger name
if the logger adapter is created via :func:`sphinx.util.logging.getLogger`.

In particular, Sphinx-related modules and third-party extensions are assumed
to do the same. Use ``MODULE`` and not ``sphinx.MODULE`` to suppress the logger
associated with the given module (e.g., ``sphinx.ext.intersphinx`` to suppress
the logger declared in the :mod:`sphinx.ext.intersphinx` module). This supports
suppressing loggers in Sphinx extensions or loggers in arbitrary modules.

Typical usage::

    # conf.py
    
    extensions = ['sphinx-zeta-suppress']

    zeta_suppress_loggers = {
        'sphinx.ext.autodoc': True                  # suppress logger
        'sphinx.ext.intersphinx': ['INFO', 'ERROR'] # specific levels
    }

    zeta_suppress_records = [
        'error: .+',
        ['sphinx.ext.intersphinx', '.*Name or service not known$']
    ]
    
Configuration values
====================

.. confval:: zeta_suppress_loggers = {}

    A dictionary describing which logger to suppress, possibly partially.

    .. code-block::

        # suppress messages from 'sphinx.ext.autodoc'
        zeta_suppress_loggers = {'sphinx.ext.autodoc': True}

        # suppress INFO and ERROR messages from 'sphinx.ext.autodoc'
        zeta_suppress_loggers = {'sphinx.ext.autodoc': ['INFO', 'ERROR']}

.. confval:: zeta_suppress_protect = []

    A list of module names that are known to contain a Sphinx logger but
    that will never be suppressed automatically. This is typically useful
    when an extension contains submodules declaring loggers which, when
    imported, result in undesirable side-effects.

.. confval:: zeta_suppress_records = []

    A list of message patterns to suppress, possibly filtered by logger.

    .. code-block::

        # suppress messages matching 'error: .*' and 'warning: .*'
        zeta_suppress_records = ['error: .*', 'warning: .*']

        # suppress messages issued by 'sphinx.ext.intersphinx'
        zeta_suppress_records = [('sphinx.ext.intersphinx', '.*')]
