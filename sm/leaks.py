#   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

############################################################################
# Preprocessing phase: locate places where rvalues are leaked, for
# later use by $leaked/LeakedPattern
############################################################################

import gcc


def get_retval_aliases(ctxt, supernode):
    exitstmtnode = supernode.stmtg.exit
    retval = exitstmtnode.returnval
    if retval is None:
        # No return value
        return frozenset()

    retval = retval.var
    ctxt.debug('retval: %s' % retval)
    from sm.facts import get_aliases
    exitsupernode = ctxt.graph.supernode_for_stmtnode[exitstmtnode]
    return get_aliases(exitsupernode.facts, retval)

def find_leaks(ctxt):
    # Set up "leaks" attribute of edges within the graph, to the set of vars
    # that "leak" along that edge.
    #
    # Currently this is extremely simplistic:
    # locals are leaked at end of a function, unless they've been
    # written elsewhere
    # FIXME: don't leak vars that have been written to elsewhere
    # FIXME: do leak when a var is overwritten

    ctxt.log('find_leaks()')

    with ctxt.indent():
        for edge in ctxt.graph.edges:
            edge.leaks = set()
            # Locate ends of functions
            # We have to put it on the dstnode, since ExitNode itself has None for a stmt
            # and checkers are only run IIRC on nodes that have a non-None stmt
            from gccutils.graph import ExitNode
            if isinstance(edge.dstnode.innernode, ExitNode):
                retval_aliases = get_retval_aliases(ctxt, edge.dstnode)
                for vardecl in edge.dstnode.function.local_decls:
                    ctxt.debug('considering vardecl: %s' % vardecl)
                    if vardecl in retval_aliases:
                        ctxt.debug('alias of return value: not leaked')
                    else:
                        ctxt.debug('leaving scope of local: %s' % vardecl)
                        from sm.facts import is_referenced_externally
                        if is_referenced_externally(ctxt, vardecl, edge.dstnode.facts):
                            ctxt.debug('%s is referenced externally: not leaked' % vardecl)
                        else:
                            edge.leaks.add(vardecl)
                        # FIXME: what if the return value isn't used?
                        # FIXME: use SSA, locate anything asssigned to the retval?
