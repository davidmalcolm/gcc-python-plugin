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
# Solver: what states are possible at each location?
############################################################################

import gcc

from gccutils import DotPrettyPrinter, invoke_dot
from gccutils.graph import Graph, Node, Edge, \
    ExitNode, \
    CallToReturnSiteEdge, CallToStart, ExitToReturnSite
from gccutils.dot import to_html

from libcpychecker.absinterp import Location, get_locations

import sm.checker
import sm.parser

class StateVar:
    def __init__(self, state):
        self.state = state

    def __repr__(self):
        return 'StateVar(%r)' % self.state

    def copy(self):
        return StateVar(self.state)

    def __eq__(self, other):
        if isinstance(other, StateVar):
            # Note that although two StateVars may have equal state, we
            # also are about identity.
            return self.state == other.state

    def __hash__(self):
        return hash(self.state)

class Shape:
    def __init__(self, ctxt):
        self.ctxt = ctxt

        # a dict mapping from vars -> StateVar instances
        self._dict = {}
        # initial state is empty, an eligible var that isn't listed is assumed
        # to have its own unique StateVar value in the default state

        # FIXME:
        # The reverse mapping, from StateVar instances to list of vars
        # self._aliases = {}

    def __hash__(self):
        result = 0
        for k, v in self._dict.iteritems():
            result ^= hash(k)
            result ^= hash(v)
        return result

    def __eq__(self, other):
        if isinstance(other, Shape):
            return self._dict == other._dict

    def __ne__(self, other):
        if not isinstance(other, Shape):
            return True
        return self._dict != other._dict

    def __str__(self):
        mapping = ', '.join(['%s:%s' % (var, statevar.state)
                          for var, statevar in self._dict.iteritems()])
        return '{%s}' % mapping

    def __repr__(self):
        return repr(self._dict)

    def copy(self):
        clone = Shape(self.ctxt)
        # 1st pass: clone the ShapeVar instances:
        shapevars = {}
        for shapevar in self._dict.values():
            shapevars[id(shapevar)] = shapevar.copy()

        # 2nd pass: update the new dict to point at the new ShapeVar instances,
        # preserving the aliasing within this dict (but breaking the aliasing
        # between old and new copies of the dict, so that when we change the
        # new Shape's values, we aren't changing the old Shape's values:
        for var, shapevar in self._dict.iteritems():
            clone._dict[var] = shapevars[id(shapevar)]

        return clone

    def get_state(self, var):
        assert isinstance(var, (gcc.VarDecl, gcc.ParmDecl))
        if var in self._dict:
            return self._dict[var].state
        return self.ctxt.get_default_state()

    def set_state(self, var, state):
        assert isinstance(var, (gcc.VarDecl, gcc.ParmDecl))
        if var in self._dict:
            # update existing StateVar (so that the change can be seen by
            # aliases):
            self._dict[var].state = state
        else:
            self._dict[var] = StateVar(state)

    def assign_var(self, dst, src):
        # print('Shape.assign_var(%r, %r)' % (dst, src))
        if src not in self._dict:
            # Set a state, so that we can track that dst is now aliased to src
            self.set_state(src, self.ctxt.get_default_state())
        self._dict[dst] = self._dict[src]

    def purge_locals(self, fun):
        vars_ = fun.local_decls + fun.decl.arguments
        for var in vars_:
            if var in self._dict:
                del self._dict[var]

class ExplodedGraph(Graph):
    """
    A graph of (innernode, shape) pairs, where "innernode" refers to
    nodes in an underlying graph (e.g. a StmtGraph or a Supergraph)
    """
    def __init__(self, ctxt):
        Graph.__init__(self)

        self.ctxt = ctxt

        # Mapping from (innernode, shape) to ExplodedNode:
        self._nodedict = {}

        # Set of (srcexpnode, dstexpnode, match) tuples, where pattern can be None:
        self._edgeset = set()

        self.entrypoints = []

        # List of ExplodedNode still to be processed by solver
        self.worklist = []

    def _make_edge(self, srcexpnode, dstexpnode, inneredge, match):
        return ExplodedEdge(srcexpnode, dstexpnode, inneredge, match)

    def lazily_add_node(self, innernode, shape):
        from gccutils.graph import SupergraphNode
        assert isinstance(innernode, SupergraphNode)
        assert isinstance(shape, Shape)
        key = (innernode, shape)
        if key not in self._nodedict:
            expnode = self.add_node(ExplodedNode(innernode, shape))
            self._nodedict[key] = expnode
            self.worklist.append(expnode)
        return self._nodedict[key]

    def lazily_add_edge(self, srcexpnode, dstexpnode, inneredge, match):
        if match:
            assert isinstance(match, sm.checker.Match)
        key = (srcexpnode, dstexpnode, match)
        if key not in self._edgeset:
            e = self.add_edge(srcexpnode, dstexpnode, inneredge, match)
            self._edgeset.add(key)

    def get_shortest_path_to(self, dstexpnode):
        result = None
        for srcexpnode in self.entrypoints:
            path = self.get_shortest_path(srcexpnode, dstexpnode)
            if path:
                if result:
                    if len(path) < len(result):
                        result = path
                else:
                    result = path
        return result

class ExplodedNode(Node):
    def __init__(self, innernode, shape):
        Node.__init__(self)
        self.innernode = innernode
        self.shape = shape

    def __repr__(self):
        return 'ExplodedNode(%r, %r)' % (self.innernode, self.shape)

    def __str__(self):
        return 'ExplodedNode(%s, %s)' % (self.innernode, self.shape)

    def get_gcc_loc(self):
        return self.innernode.get_gcc_loc()

    def to_dot_label(self, ctxt):
        from gccutils.dot import Table, Tr, Td, Text, Br

        table = Table()
        tr = table.add_child(Tr())
        tr.add_child(Td([Text('SHAPE: %s' % str(self.shape))]))
        tr = table.add_child(Tr())
        innerhtml = self.innernode.to_dot_html(ctxt)
        if innerhtml:
            tr.add_child(Td([innerhtml]))
        else:
            tr.add_child(Td([Text(str(self.innernode))]))
        return '<font face="monospace">' + table.to_html() + '</font>\n'

    def get_subgraph(self, ctxt):
        if 0:
            # group by function:
            return self.innernode.get_subgraph(ctxt)
        else:
            # ungrouped:
            return None

    @property
    def function(self):
        return self.innernode.function

class ExplodedEdge(Edge):
    def __init__(self, srcexpnode, dstexpnode, inneredge, match):
        Edge.__init__(self, srcexpnode, dstexpnode)
        self.inneredge = inneredge
        if match:
            assert isinstance(match, sm.checker.Match)
        self.match = match

    def __repr__(self):
        return ('%s(srcnode=%r, dstnode=%r, inneredge=%r, match=%r)'
                % (self.__class__.__name__, self.srcnode, self.dstnode,
                   self.inneredge.__class__, self.match))

    def to_dot_label(self, ctxt):
        result = self.inneredge.to_dot_label(ctxt)
        if self.match:
            result += to_html(self.match.description(ctxt))
        if self.srcnode.shape != self.dstnode.shape:
            result += to_html(' %s -> %s' % (self.srcnode.shape, self.dstnode.shape))
        return result.strip()

    def to_dot_attrs(self, ctxt):
        return self.inneredge.to_dot_attrs(ctxt)

class MatchContext:
    """
    A match of a specific rule, to be supplied to Outcome.apply()
    """
    def __init__(self, match, expgraph, srcexpnode, inneredge):
        from sm.checker import Match
        from gccutils.graph import SupergraphEdge
        assert isinstance(match, Match)
        assert isinstance(expgraph, ExplodedGraph)
        assert isinstance(srcexpnode, ExplodedNode)
        assert isinstance(inneredge, SupergraphEdge)
        self.match = match
        self.expgraph = expgraph
        self.srcexpnode = srcexpnode
        self.inneredge = inneredge

    @property
    def srcshape(self):
        return self.srcexpnode.shape

    @property
    def dstnode(self):
        return self.inneredge.dstnode

def make_exploded_graph(ctxt, innergraph):
    expgraph = ExplodedGraph(ctxt)
    for entry in innergraph.get_entry_nodes():
        expnode = expgraph.lazily_add_node(entry, Shape(ctxt)) # initial shape
        expgraph.entrypoints.append(expnode)
    while expgraph.worklist:
        srcexpnode = expgraph.worklist.pop()
        srcnode = srcexpnode.innernode
        #assert isinstance(srcnode, Node)
        stmt = srcnode.get_stmt()
        for edge in srcnode.succs:
            dstnode = edge.dstnode
            if 0:
                print('  edge from: %s' % srcnode)
                print('         to: %s' % dstnode)
            srcshape = srcexpnode.shape

            # Handle interprocedural edges:
            if isinstance(edge, CallToReturnSiteEdge):
                # Ignore the intraprocedural edge for a function call:
                continue
            elif isinstance(edge, CallToStart):
                # Alias the parameters with the arguments as necessary, so
                # e.g. a function that free()s an arg has the caller's var
                # marked as free also:
                dstshape = srcshape.copy()
                assert isinstance(srcnode.stmt, gcc.GimpleCall)
                # print(srcnode.stmt)
                for param, arg  in zip(srcnode.stmt.fndecl.arguments, srcnode.stmt.args):
                    # FIXME: change fndecl.arguments to fndecl.parameters
                    if 0:
                        print('  param: %r' % param)
                        print('  arg: %r' % arg)
                    if ctxt.is_stateful_var(arg):
                        dstshape.assign_var(param, arg)
                # print('dstshape: %r' % dstshape)
                dstexpnode = expgraph.lazily_add_node(dstnode, dstshape)
                expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode,
                                                   edge, None)
                continue
            elif isinstance(edge, ExitToReturnSite):
                dstshape = srcshape.copy()
                # Propagate state through the return value:
                # print('edge.calling_stmtnode: %s' % edge.calling_stmtnode)
                if edge.calling_stmtnode.stmt.lhs:
                    exitsupernode = edge.srcnode
                    assert isinstance(exitsupernode.innernode, ExitNode)
                    returnstmtnode = exitsupernode.innernode.returnnode
                    assert isinstance(returnstmtnode.stmt, gcc.GimpleReturn)
                    retval = returnstmtnode.stmt.retval
                    if ctxt.is_stateful_var(retval):
                        dstshape.assign_var(edge.calling_stmtnode.stmt.lhs, retval)
                # ...and purge all local state:
                dstshape.purge_locals(edge.srcnode.function)
                dstexpnode = expgraph.lazily_add_node(dstnode, dstshape)
                expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode,
                                                   edge, None)
                continue

            # Handle simple assignments so that variables inherit state:
            if isinstance(stmt, gcc.GimpleAssign):
                if 0:
                    print(stmt)
                    print('stmt.lhs: %r' % stmt.lhs)
                    print('stmt.rhs: %r' % stmt.rhs)
                    print('stmt.exprcode: %r' % stmt.exprcode)
                if stmt.exprcode == gcc.VarDecl:
                    dstshape = srcshape.copy()
                    dstshape.assign_var(stmt.lhs, stmt.rhs[0])
                    dstexpnode = expgraph.lazily_add_node(dstnode, dstshape)
                    expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode,
                                                       edge, None)
                    continue

            matches = []
            for sc in ctxt.sm.stateclauses:
                # Locate any rules that could apply, regardless of the current
                # state:
                for pr in sc.patternrulelist:
                    # print('%r: %r' % (srcshape, pr))
                    # For now, skip interprocedural calls and the
                    # ENTRY/EXIT nodes:
                    if not stmt:
                        continue
                    # Now see if the rules apply for the current state:
                    for match in pr.pattern.iter_matches(stmt, edge, ctxt):
                        # print('pr.pattern: %r' % pr.pattern)
                        # print('match: %r' % match)
                        # print(match.var)
                        srcstate = srcshape.get_state(match.var)
                        if srcstate in sc.statelist:
                            assert len(pr.outcomes) > 0
                            mctxt = MatchContext(match, expgraph, srcexpnode, edge)
                            for outcome in pr.outcomes:
                                outcome.apply(mctxt)
                            matches.append(pr)
            if not matches:
                dstexpnode = expgraph.lazily_add_node(dstnode, srcshape)
                expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode,
                                                   edge, None)
    return expgraph

class Error:
    # A stored error
    def __init__(self, expnode, match, msg):
        self.expnode = expnode
        self.match = match
        self.msg = msg

    @property
    def gccloc(self):
        return self.expnode.innernode.get_gcc_loc()

    @property
    def function(self):
        return self.expnode.function

    def __lt__(self, other):
        # Provide a sort order, so that they sort into source order
        return self.gccloc < other.gccloc

    def emit(self, ctxt, expgraph):
        """
        Display the error
        """
        loc = self.gccloc
        gcc.error(loc, self.msg)
        path = expgraph.get_shortest_path_to(self.expnode)
        # print('path: %r' % path)
        for expedge in path:
            # print(expnode)
            # FIXME: this needs to respect the StateVar, in case of a returned value...
            # we need to track changes to the value of the specific StateVar (but we can't, because it's a copy each time.... grrr...)
            # we should also report relevant aliasing information
            # ("foo" passed to fn bar as "baz"; "baz" returned from fn bar into "foo")
            # TODO: backtrace down the path, tracking the StateVar aliases of interest...
            srcstate = expedge.srcnode.shape.get_state(self.match.var)
            dststate = expedge.dstnode.shape.get_state(self.match.var)
            if srcstate != dststate:
                gccloc = expedge.srcnode.innernode.get_gcc_loc()
                if gccloc:
                    if 1:
                        # Describe state change:
                        desc = expedge.match.description(ctxt)
                    else:
                        # Debugging information on state change:
                        desc = ('%s: %s -> %s'
                               % (ctxt.sm.name, expedge.srcnode.state, expedge.dstnode.state))
                    gcc.inform(gccloc, desc)

        # repeat the message at the end of the path:
        if len(path) > 1:
            gcc.inform(path[-1].dstnode.innernode.get_gcc_loc(), self.msg)

class Context:
    # An sm.checker.Sm (do we need any other context?)

    # in context, with a mapping from its vars to gcc.VarDecl
    # (or ParmDecl) instances
    def __init__(self, sm): # , var):
        #assert isinstance(var, (gcc.VarDecl, gcc.ParmDecl))
        self.sm = sm
        #self.var = var
        self.statenames = list(sm.iter_states())

        # Store the errors so that we can play them back in source order
        # (for greater predicability of selftests):
        self._errors = []

    def __repr__(self):
        return 'Context(%r)' % (self.statenames, )

    def add_error(self, expnode, match, msg):
        self._errors.append(Error(expnode, match, msg))

    def emit_errors(self, expgraph):
        curfun = None
        curfile = None
        for error in self._errors:
            gccloc = error.gccloc
            if error.function != curfun or gccloc.file != curfile:
                # Fake the function-based output
                # e.g.:
                #    "tests/sm/examples/malloc-checker/input.c: In function 'use_after_free':"
                import sys
                sys.stderr.write("%s: In function '%s':\n"
                                 % (gccloc.file, error.function.decl.name))
                curfun = error.function
                curfile = gccloc.file
            error.emit(self, expgraph)

    def compare(self, gccexpr, smexpr):
        #print('compare(%r, %r)' % (gccexpr, smexpr))
        #print('self.var: %r' % self.var)
        if isinstance(gccexpr, (gcc.VarDecl, gcc.ParmDecl)):
            #if gccexpr == self.var:
            # print '%r' % self.sm.varclauses.name
            if smexpr == self.sm.varclauses.name:
                return True

        if isinstance(gccexpr, gcc.IntegerCst) and isinstance(smexpr, (int, long)):
            if gccexpr.constant == smexpr:
                return True

        return False
        print('compare:')
        print('  gccexpr: %r' % gccexpr)
        print('  smexpr: %r' % smexpr)
        raise UnhandledComparison()

    def describe(self, smexpr):
        return str(smexpr)

        return 'Context.describe()'
        if smexpr == self.sm.varclauses.name:
            return str(self.var)
        if isinstance(smexpr, (int, long)):
            return str(smexpr)
        print('smexpr: %r' % smexpr)
        raise UnhandledDescription()

    def get_default_state(self):
        return self.statenames[0]

    def is_stateful_var(self, gccexpr):
        '''
        Is this gcc.Tree of a kind that has state according to the current sm?
        '''
        if isinstance(gccexpr, (gcc.VarDecl, gcc.ParmDecl)):
            if isinstance(gccexpr.type, gcc.PointerType):
                # TODO: the sm may impose further constraints
                return True

def solve(ctxt, graph, name):
    # print('running %s' % ctxt.sm.name)
    expgraph = make_exploded_graph(ctxt, graph)
    if 0:
        # Debug: view the exploded graph:
        dot = expgraph.to_dot(name, ctxt)
        # print(dot)
        invoke_dot(dot, name)

    # Now report the errors, grouped by function, and in source order:
    ctxt._errors.sort()

    ctxt.emit_errors(expgraph)
