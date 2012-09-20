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
from gccutils.graph import Graph, Node, Edge
from gccutils.dot import to_html

from libcpychecker.absinterp import Location, get_locations

import sm.checker
import sm.parser

class ExplodedGraph(Graph):
    """
    A graph of (innernode, state) pairs, where "innernode" refers to
    nodes in an underlying graph (e.g. a CFG)
    """
    def __init__(self):
        Graph.__init__(self)
        # Mapping from (innernode, state) to ExplodedNode:
        self._nodedict = {}

        # Set of (srcnode, dstnode, pattern) tuples, where pattern can be None:
        self._edgeset = set()

    def _make_edge(self, srcnode, dstnode, pattern):
        return ExplodedEdge(srcnode, dstnode, pattern)

    def lazily_add_node(self, innernode, state):
        key = (innernode, state)
        if key not in self._nodedict:
            node = self.add_node(ExplodedNode(innernode, state))
            self._nodedict[key] = node
        return self._nodedict[key]

    def lazily_add_edge(self, srcnode, dstnode, pattern):
        if pattern:
            assert isinstance(pattern, sm.checker.Pattern)
        key = (srcnode, dstnode, pattern)
        if key not in self._edgeset:
            e = self.add_edge(srcnode, dstnode, pattern)
            self._edgeset.add(key)

class ExplodedNode(Node):
    def __init__(self, innernode, state):
        Node.__init__(self)
        self.innernode = innernode
        self.state = state

    def __repr__(self):
        return 'ExplodedNode(%r, %r)' % (self.innernode, self.state)

    def to_dot_label(self, ctxt):
        result = '<font face="monospace"><table cellborder="0" border="0" cellspacing="0">\n'
        result += ('<tr> <td>%s</td> <td>%s</td> </tr>\n'
                   % (to_html(str(self.innernode)), to_html(str(self.state))))
        from gccutils import get_src_for_loc
        stmt = self.innernode.get_stmt()
        loc = self.innernode.get_gcc_loc()
        if loc:
            code = get_src_for_loc(loc).rstrip()
            pseudohtml = to_html(code)
            result += ('<tr><td align="left">'
                       + to_html('%4i ' % stmt.loc.line)
                       + pseudohtml
                       + '<br/>'
                       + (' ' * (5 + stmt.loc.column-1)) + '^'
                       + '</td></tr>')
        #result += '<tr><td></td>' + to_html(stmt, stmtidx) + '</tr>\n'
        result += '</table></font>\n'
        return result

class ExplodedEdge(Edge):
    def __init__(self, srcnode, dstnode, pattern):
        Edge.__init__(self, srcnode, dstnode)
        if pattern:
            assert isinstance(pattern, sm.checker.Pattern)
        self.pattern = pattern

    def to_dot_label(self, ctxt):
        if self.pattern:
            return to_html(self.pattern.description(ctxt))
        if self.srcnode.state != self.dstnode.state:
            return to_html('%s -> %s' % (self.srcnode.state, self.dstnode.state))
        else:
            return ''

def make_exploded_graph(fun, ctxt):
    locations = get_locations(fun) # these will be our nodes

    # The initial state is the first block after entry (which has no statements):
    initbb = fun.cfg.entry.succs[0].dest
    initloc = Location(initbb, 0)
    expgraph = ExplodedGraph()
    expnode = expgraph.lazily_add_node(initloc, ctxt.statenames[0]) # initial state
    worklist = [expnode]
    while worklist:
        def lazily_add_node(loc, state):
            if (loc, state) not in expgraph._nodedict:
                expnode = expgraph.lazily_add_node(loc, state)
                worklist.append(expnode)
            else:
                # (won't do anything)
                expnode = expgraph.lazily_add_node(loc, state)
            return expnode
        srcexpnode = worklist.pop()
        srcloc = srcexpnode.innernode
        stmt = srcloc.get_stmt()
        for dstloc, edge in srcloc.next_locs():
            if 0:
                print('  edge from: %s' % srcloc)
                print('         to: %s' % dstloc)
            srcstate = srcexpnode.state
            matches = []
            for sc in ctxt.sm.stateclauses:
                if srcstate in sc.statelist:
                    for pr in sc.patternrulelist:
                        # print('%r: %r' %(srcstate, pr))
                        if pr.pattern.matched_by(stmt, edge, ctxt):
                            assert len(pr.outcomes) > 0
                            for outcome in pr.outcomes:
                                # print 'outcome: %r' % outcome
                                def handle_outcome(outcome):
                                    # print('handle_outcome(%r)' % outcome)
                                    if isinstance(outcome, sm.checker.BooleanOutcome):
                                        if 0:
                                            print(edge.true_value)
                                            print(edge.false_value)
                                            print(outcome.guard)
                                        if edge.true_value and outcome.guard:
                                            handle_outcome(outcome.outcome)
                                        if edge.false_value and not outcome.guard:
                                            handle_outcome(outcome.outcome)
                                    elif isinstance(outcome, sm.checker.TransitionTo):
                                        # print('transition to %s' % outcome.state)
                                        dststate = outcome.state
                                        dstexpnode = lazily_add_node(dstloc, dststate)
                                        expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode,
                                                                           pr.pattern)
                                    elif isinstance(outcome, sm.checker.PythonOutcome):
                                        ctxt.srcloc = srcloc
                                        expnode = expgraph.lazily_add_node(srcloc, srcstate)
                                        outcome.run(ctxt, expgraph, expnode)
                                    else:
                                        print(outcome)
                                        raise UnknownOutcome(outcome)
                                handle_outcome(outcome)
                            matches.append(pr)
            if not matches:
                dstexpnode = lazily_add_node(dstloc, srcstate)
                expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode, None)
    return expgraph

def solve(fun, ctxt):
    if 0:
        solver = Solver(fun, ctxt)
        solver.solve()

    if 1:
        expgraph = make_exploded_graph(fun, ctxt)
        if 0:
            # Debug: view the exploded graph:
            name = '%s_on_%s_%s' % (ctxt.sm.name, fun.decl.name, ctxt.var.name)
            dot = expgraph.to_dot(name, ctxt)
            # print(dot)
            invoke_dot(dot, name)

class Context:
    # An sm.checker.Sm in context, with a mapping from its vars to gcc.VarDecl
    # (or ParmDecl) instances
    def __init__(self, sm, var):
        assert isinstance(var, (gcc.VarDecl, gcc.ParmDecl))
        self.sm = sm
        self.var = var
        self.statenames = list(sm.iter_states())

    def __repr__(self):
        return 'Context(%r)' % (self.statenames, )

    def compare(self, gccexpr, smexpr):
        # print('compare(%r, %r)' % (gccexpr, smexpr))
        # print('self.var: %r' % self.var)
        if gccexpr == self.var:
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
        if smexpr == self.sm.varclauses.name:
            return str(self.var)
        if isinstance(smexpr, (int, long)):
            return str(smexpr)
        print('smexpr: %r' % smexpr)
        raise UnhandledDescription()
