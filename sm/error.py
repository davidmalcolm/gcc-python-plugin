#   Copyright 2012, 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012, 2013 Red Hat, Inc.
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

import gcc

from gccutils.graph.stmtgraph import ExitNode, SplitPhiNode
from gccutils.graph.supergraph import CallNode, ReturnNode, \
    CallToStart, ExitToReturnSite

from sm.reporter import Report, Note
from sm.utils import simplify, stateset_to_str, get_retval_aliases

class PathAnnotations:
    """
    Important events along a path
    """
    def __init__(self, ctxt, error, path):
        # Determine important events within the path
        # Walk backwards along it, tracking the expression of importance
        # and its state
        ctxt.debug('error.match: %s', error.match)
        expr = error.match.get_stateful_gccvar(ctxt)
        states = frozenset([error.state])
        ctxt.debug('expr, states: %s, %s', expr, states)
        self._significant_for_node = {path[-1].dstnode : (expr, states)}
        for edge in path[::-1]:
            ctxt.debug('edge: %s', edge)
            ctxt.debug('  edge.inneredge: %s', edge.inneredge)
            ctxt.debug('  edge.match: %s', edge.match)
            srcnode = edge.srcnode
            dstnode = edge.dstnode
            inneredge = edge.inneredge
            stmt = srcnode.stmt
            if isinstance(edge.inneredge, CallToStart):
                # Update the expr of interest based on param/arg mapping:
                for param, arg  in zip(srcnode.stmt.fndecl.arguments,
                                       srcnode.stmt.args):
                    param = simplify(param)
                    arg = simplify(arg)
                    if expr == param:
                        expr = arg
            elif isinstance(edge.inneredge, ExitToReturnSite):
                # Was state propagated through the return value?
                if inneredge.calling_stmtnode.stmt.lhs:
                    exitsupernode = inneredge.srcnode
                    assert isinstance(exitsupernode.innernode, ExitNode)
                    retval = simplify(exitsupernode.innernode.returnval)
                    lhs = simplify(inneredge.calling_stmtnode.stmt.lhs)
                    if expr == lhs:
                        expr = retval

                # Did the params change state?
                callsite = inneredge.dstnode.callnode.innernode
                ctxt.debug('callsite: %s', callsite)
                for param, arg  in zip(callsite.stmt.fndecl.arguments,
                                       callsite.stmt.args):
                    param = simplify(param)
                    arg = simplify(arg)
                    ctxt.debug('param: %s', param)
                    ctxt.debug('arg: %s', arg)
                    if expr == arg:
                        expr = param
            elif isinstance(stmt, gcc.GimpleAssign):
                lhs = simplify(stmt.lhs)
                if stmt.exprcode == gcc.VarDecl:
                    rhs = simplify(stmt.rhs[0])
                    if expr == lhs:
                        expr = rhs
                elif stmt.exprcode == gcc.ComponentRef:
                    compref = stmt.rhs[0]
                    if expr == lhs:
                        srcsupernode = srcnode.supergraphnode
                        if ctxt.get_aliases(srcsupernode, compref) in ctxt.states_for_node[srcsupernode]._dict:
                            expr = compref
                        else:
                            expr = compref.target
            elif isinstance(stmt, gcc.GimplePhi):
                assert isinstance(srcnode.stmtnode, SplitPhiNode)
                rhs = simplify(srcnode.stmtnode.rhs)
                ctxt.debug('  rhs: %r', rhs)
                lhs = simplify(stmt.lhs)
                ctxt.debug('  lhs: %r', lhs)
                if expr == lhs:
                    expr = rhs
            if edge.match:
                if edge.match.get_stateful_gccvar(ctxt) == expr:
                    # This is a match affecting the expr of interest:
                    states = srcnode.get_states_for_expr(ctxt, expr)

            ctxt.debug('  expr, states: %s, %s', expr, states)
            self._significant_for_node[srcnode] = (expr, states)

    def get_significant_expr_at(self, node):
        return self._significant_for_node[node][0]

    def get_significant_states_at(self, node):
        return self._significant_for_node[node][1]

class Error:
    # A stored error
    def __init__(self, srcnode, match, msg, state, cwe, sm_filename, sm_lineno):
        self.srcnode = srcnode
        self.match = match
        self.msg = msg
        self.state = state

        # cwe can be None, or a str of the form "CWE-[0-9]+"
        # e.g. "CWE-590"  aka "Free of Memory not on the Heap"
        # see http://cwe.mitre.org/data/definitions/590.html
        self.cwe = cwe

        # Metadata about where in the sm script this error was emitted:
        self.sm_filename = sm_filename # so that you can import helper files
        self.sm_lineno = sm_lineno

    @property
    def gccloc(self):
        gccloc = self.srcnode.get_gcc_loc()
        if gccloc is None:
            gccloc = self.function.end
        return gccloc

    @property
    def function(self):
        return self.srcnode.function

    def __lt__(self, other):
        # Provide a sort order, so that they sort into source order

        # First sort by location:
        if self.gccloc < other.gccloc:
            return True
        elif self.gccloc > other.gccloc:
            return False

        # Failing that, sort by message:
        return self.msg < other.msg

    def __eq__(self, other):
        if self.srcnode == other.srcnode:
            if self.match == other.match:
                if self.msg == other.msg:
                    if self.state == other.state:
                        return True

    def __hash__(self):
        return hash(self.srcnode) ^ hash(self.match) ^ hash(self.msg) ^ hash(self.state)

    def make_report(self, ctxt, solution):
        """
        Generate a Report instance (or None if it's impossible)
        """
        notes = []
        loc = self.gccloc
        stateful_gccvar = self.match.get_stateful_gccvar(ctxt)
        path = solution.get_shortest_path_to(self.srcnode,
                                             ctxt.get_aliases(self.srcnode, stateful_gccvar),
                                             self.state)
        ctxt.debug('path: %r', path)
        if path is None:
            # unreachable:
            ctxt.log('unreachable error')
            return None

        # Figure out the interesting events along the path:
        pa = PathAnnotations(ctxt, self, path)

        # Now generate a report, using the significant events:
        for edge in path:
            srcnode = edge.srcnode
            srcsupernode = edge.srcnode.innernode
            srcgccloc = srcsupernode.get_gcc_loc()
            srcexpr = pa.get_significant_expr_at(srcnode)
            srcstates = pa.get_significant_states_at(srcnode)

            dstnode = edge.dstnode
            dstsupernode = edge.dstnode.innernode
            dstgccloc = dstsupernode.get_gcc_loc()
            dstexpr = pa.get_significant_expr_at(dstnode)
            dststates = pa.get_significant_states_at(dstnode)

            with ctxt.indent():
                ctxt.debug('edge from:')
                with ctxt.indent():
                    ctxt.debug('srcnode: %s', srcsupernode)
                    ctxt.debug('pa._significant_for_node[srcnode]: %s',
                               pa._significant_for_node[srcnode])
                    ctxt.debug('srcstates: %s', srcstates)
                    ctxt.debug('srcloc: %s', srcgccloc)
                ctxt.debug('to:')
                with ctxt.indent():
                    ctxt.debug('dstnode: %s', dstsupernode)
                    ctxt.debug('pa._significant_for_node[dstnode]: %s',
                               pa._significant_for_node[dstnode])
                    ctxt.debug('dststates: %s', dststates)
                    ctxt.debug('dstloc: %s', dstgccloc)

            gccloc = srcgccloc
            desc = ''
            if isinstance(srcsupernode, CallNode):
                #if gccloc is None:
                #    gccloc = dstgccloc
                desc= ('call from %s() to %s()'
                       % (srcsupernode.function.decl.name,
                          dstsupernode.function.decl.name))
            elif isinstance(dstsupernode, ReturnNode):
                if gccloc is None:
                    gccloc = dstgccloc
                desc =  ('return from %s() to %s()'
                         % (srcsupernode.function.decl.name,
                            dstsupernode.function.decl.name))
            if gccloc:
                if pa._significant_for_node[srcnode] != pa._significant_for_node[dstnode]:
                    if edge.match:
                        # Describe state change:
                        if desc:
                            desc += ': '
                        desc += edge.match.description(ctxt)
                        notes.append(Note(gccloc, desc))
                        continue

                    # We care about state changes, or state propagations,
                    # but we don't care about propagations of the "start" state:
                    newstates = dststates - srcstates
                    ctxt.debug('newstates: %s', newstates)
                    if newstates or ctxt.get_default_state() not in srcstates:
                        # Debugging information on state change:
                        if desc:
                            desc += ': '
                        desc += ('state of %s (%s) propagated to %s'
                                 % (gccexpr_to_str(ctxt, srcsupernode, srcexpr),
                                    ' or '.join(['"%s"' % state for state in srcstates]),
                                    gccexpr_to_str(ctxt, dstsupernode, dstexpr)))
                        notes.append(Note(gccloc, desc))
                        continue
                # Debugging information on state change:
                if 0:
                    desc += ('%s: %s:%s -> %s:%s'
                             % (ctxt.sm.name,
                                srcexpr, stateset_to_str(srcstates),
                                dstexpr, stateset_to_str(dststates)))
                    notes.append(Note(gccloc, desc))
                else:
                    if desc:
                        notes.append(Note(gccloc, desc))
            continue

        # repeat the message at the end of the path, if anything else has
        # been said:
        if notes:
            gccloc = path[-1].dstnode.innernode.get_gcc_loc()
            if gccloc:
                notes.append(Note(gccloc, self.msg))

        return Report(ctxt.sm, self, notes)


def get_user_expr(equivcls):
    # What's the best expr within the equivcls for use in a description?
    # named locals (not temporaries):
    if equivcls is None:
        return 'None'

    for expr in equivcls:
        if isinstance(expr, gcc.VarDecl) and expr.name:
            return expr

    # composites:
    for expr in equivcls:
        if isinstance(expr, gcc.ComponentRef):
            return expr

    # otherwise, pick the first:
    for expr in equivcls:
        return expr

def equivcls_to_user_str(ctxt, supernode, equivcls):
    ctxt.debug('equivcls_to_user_str: node: %s gccexpr: %s',
               supernode, equivcls)
    expr = get_user_expr(equivcls)
    return gccexpr_to_str(ctxt, supernode, expr)

def gccexpr_to_str(ctxt, supernode, gccexpr):
    ctxt.debug('gccexpr_to_str: node: %s gccexpr: %s', supernode, gccexpr)
    if isinstance(gccexpr, gcc.VarDecl):
        if gccexpr.name:
            return str(gccexpr)
        else:
            # We have a temporary variable.
            # Try to use a better name if the node "knows" where the
            # temporary came from:
            aliases = ctxt.get_aliases(supernode, gccexpr)
            for alias in aliases:
                if isinstance(alias, gcc.VarDecl):
                    if alias.name:
                        return str(alias)
                if isinstance(alias, gcc.ComponentRef):
                    return str(alias)

            # Is it the return value?
            ctxt.debug('get_retval_aliases: %s', get_retval_aliases(ctxt, supernode))
            if gccexpr in get_retval_aliases(ctxt, supernode):
                return 'return value'

            # Couldn't find a better name.  Identify it as a temporary,
            # and give the specific ID in parentheses, since this is useful
            # for debugging:
            return 'temporary (%s)' % gccexpr

    return str(gccexpr)
