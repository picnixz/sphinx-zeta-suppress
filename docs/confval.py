r"""
Implement the :rst:dir:`confval` Sphinx directive.

.. rst:directive:: .. confval:: name = default

    Document a Sphinx or third-party extension configuration value.

.. rst:role:: confval

    Cross-referencing role associated with the :rst:dir:`confval` directive.
"""

__all__ = ()

import re
from typing import TYPE_CHECKING

import docutils.nodes as nodes
import sphinx.addnodes as addnodes

if TYPE_CHECKING:
    from docutils.nodes import Node
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment

_match_confval_default_value = re.compile(r'([^ ]+)\s*=\s*(.*)')
_match_confval_default_value = _match_confval_default_value.match

def parse_value(env, sig, signode):
    # type: (BuildEnvironment, str, Node) -> str
    refnode = addnodes.pending_xref(
        '',
        refdomain='rst', reftype='role',
        reftarget='confval', refexplicit=False
    )
    refnode += nodes.Text('[cv]')
    env.get_domain('rst').process_field_xref(refnode)
    signode += refnode
    signode += addnodes.desc_sig_space()
    match = _match_confval_default_value(sig)
    if not match:
        signode += addnodes.desc_name(sig, sig)
        return sig

    name, default = match.groups()
    signode += addnodes.desc_name(name, name)
    signode += addnodes.desc_annotation(
        '', '',
        addnodes.desc_sig_punctuation('', ' = '),
        addnodes.desc_sig_space(),
        addnodes.desc_annotation(default, default)
    )
    return name

###############################################################################

def setup(app):
    # type: (Sphinx) -> dict
    app.add_object_type('confval', 'confval', 'pair: %s; confval', parse_value)
    return {'parallel_read_safe': True, 'parallel_write_safe': True}
