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

import gcc

from gccutils.graph import CallNode, ReturnNode

class Error:
    # A stored error
    def __init__(self, srcnode, match, msg, state):
        self.srcnode = srcnode
        self.match = match
        self.msg = msg
        self.state = state

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
        from sm.reporter import Report, Note
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

        for edge in path:
            # ctxt.debug(srcnode)
            # FIXME: this needs to respect the StateVar, in case of a returned value...
            # we need to track changes to the value of the specific StateVar (but we can't, because it's a copy each time.... grrr...)
            # we should also report relevant aliasing information
            # ("foo" passed to fn bar as "baz"; "baz" returned from fn bar into "foo")
            # TODO: backtrace down the path, tracking the StateVar aliases of interest...
            srcsupernode = edge.srcnode.innernode
            srcgccloc = srcsupernode.get_gcc_loc()
            srcequivcls = edge.srcnode.equivcls
            srcstate = edge.srcnode.state

            dstsupernode = edge.dstnode.innernode
            dstgccloc = dstsupernode.get_gcc_loc()
            dstequivcls = edge.dstnode.equivcls
            dststate = edge.dstnode.state

            with ctxt.indent():
                ctxt.debug('edge from:')
                with ctxt.indent():
                    ctxt.debug('srcnode: %s', srcsupernode)
                    ctxt.debug('equivcls: %s', srcequivcls)
                    ctxt.debug('state: %s', srcstate)
                    ctxt.debug('srcloc: %s', srcgccloc)
                ctxt.debug('to:')
                with ctxt.indent():
                    ctxt.debug('dstnode: %s', dstsupernode)
                    ctxt.debug('equivcls: %s', dstequivcls)
                    ctxt.debug('state: %s', dststate)
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
                if srcstate != dststate:
                    ctxt.log('state change!')
                    # Describe state change:
                    if edge.srcnode.match:
                        if desc:
                            desc += ': '
                        desc += edge.srcnode.match.description(ctxt)
                        notes.append(Note(gccloc, desc))
                elif get_user_expr(srcequivcls) != get_user_expr(dstequivcls) \
                        and srcstate != ctxt.get_default_state():
                    ctxt.log('equivcls change!')
                    # Debugging information on state change:
                    if desc:
                        desc += ': '
                    desc += ('state of %s ("%s") propagated to %s'
                             % (equivcls_to_user_str(ctxt, srcsupernode, srcequivcls),
                                srcstate,
                                equivcls_to_user_str(ctxt, dstsupernode, dstequivcls)))
                    notes.append(Note(gccloc, desc))
                else:
                    # Debugging information on state change:
                    if 0:
                        desc += ('%s: %s:%s -> %s:%s'
                                 % (ctxt.sm.name,
                                    srcequivcls, srcstate,
                                    dstequivcls, dststate))
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

        return Report(self, notes)


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
            from sm.leaks import get_retval_aliases
            from gccutils.graph import ExitNode

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
