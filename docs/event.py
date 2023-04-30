r"""
Implement the :rst:dir:`event` Sphinx directive.

.. rst:directive:: .. event:: name (parameters_list)

    Document a Sphinx or third-party extension event.

.. rst:role:: event

    Cross-referencing role associated with the :rst:dir:`event` directive.

Unlike the Sphinx directive, this directive does *not* support documenting
event parameters similarly to Python functions. The rationale behind is to
make it as much as lightweight as possible.
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

_match_event_signature = re.compile(r'([^ ]+)\s*\((.*)\)')
_match_event_signature = _match_event_signature.match

def parse_event(env, sig, signode):
    # type: (BuildEnvironment, str, Node) -> str
    refnode = addnodes.pending_xref(
        '',
        refdomain='rst', reftype='role',
        reftarget='event', refexplicit=False
    )
    refnode += nodes.Text('[ev]')
    env.get_domain('rst').process_field_xref(refnode)
    signode += refnode
    signode += addnodes.desc_sig_space()
    match = _match_event_signature(sig)
    if not match:
        sig = re.sub(r'\s{2,}', '', sig)
        signode += addnodes.desc_name(sig, sig)
        return sig

    name, args = match.groups()
    signode += addnodes.desc_name(name, name)
    plist = addnodes.desc_parameterlist()
    for arg in filter(None, map(str.strip, args.split(','))):
        plist += addnodes.desc_parameter(arg, arg)
    signode += plist
    return name

###############################################################################

def setup(app):
    # type: (Sphinx) -> dict
    app.add_object_type('event', 'event', 'pair: %s; event', parse_event)
    return {'parallel_read_safe': True, 'parallel_write_safe': True}
