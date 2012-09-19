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

from libcpychecker.absinterp import Location, get_locations

import sm.parser

class ExplodedGraphPrettyPrinter(DotPrettyPrinter):
    def __init__(self, expgraph, name):
        self.expgraph = expgraph
        self.name = name

    def to_dot(self):
        if hasattr(self, 'name'):
            name = self.name
        else:
            name = 'G'
        result = 'digraph %s {\n' % name
        for expnode in self.expgraph.iter_nodes():
            result += ('  %s [label=<%s>];\n'
                       % (self.expnode_to_id(expnode),
                          self.expnode_to_dot_label(expnode)))

        for expedge in self.expgraph.edges:
            result += self.expedge_to_dot(expedge)
        result += '}\n'
        return result

    def expnode_to_id(self, expnode):
        return '%s' % id(expnode)

    def expnode_to_dot_label(self, expnode):
        result = '<font face="monospace"><table cellborder="0" border="0" cellspacing="0">\n'
        result += ('<tr> <td>%s</td> <td>%s</td> </tr>\n'
                   % (self.to_html(str(expnode.node)), expnode.state))
        from gccutils import get_src_for_loc
        stmt = expnode.node.get_stmt()
        loc = expnode.node.get_gcc_loc()
        if loc:
            code = get_src_for_loc(loc).rstrip()
            pseudohtml = self.to_html(code)
            result += ('<tr><td align="left">'
                       + self.to_html('%4i ' % stmt.loc.line)
                       + pseudohtml
                       + '<br/>'
                       + (' ' * (5 + stmt.loc.column-1)) + '^'
                       + '</td></tr>')
        #result += '<tr><td></td>' + to_html(stmt, stmtidx) + '</tr>\n'
        result += '</table></font>\n'
        return result

    def expedge_to_dot(self, expedge):
        if expedge.srcexpnode.state != expedge.dstexpnode.state:
            label = self.to_html('%s -> %s' % (expedge.srcexpnode.state.name, expedge.dstexpnode.state.name))
        else:
            label = ''
        return ('    %s -> %s [label=<%s>];\n'
                % (self.expnode_to_id(expedge.srcexpnode),
                   self.expnode_to_id(expedge.dstexpnode),
                   label))

class ExplodedGraph:
    """Like a CFG, but with (node, state) pairs"""
    def __init__(self):
        # Mapping from (node, state) to ExplodedNode:
        self.nodedict = {}
        self.edges = set()
        self.initial = None

    def lazily_add_node(self, node, state):
        key = (node, state)
        if key not in self.nodedict:
            self.nodedict[key] = ExplodedNode(node, state)
            if not self.initial:
                self.initial = self.nodedict[key]
        return self.nodedict[key]

    def lazily_add_edge(self, srcnode, dstnode):
        self.edges.add(ExplodedEdge(srcnode, dstnode))

    def iter_nodes(self):
        for key in self.nodedict:
            yield self.nodedict[key]

    def to_dot(self):
        pp = ExplodedGraphPrettyPrinter(self, 'foo')
        return pp.to_dot()

    def get_shortest_path(self, dstnode, dststate):
        '''
        Locate paths that go from the initial state to the
        destination (node, state) pair
        '''
        # Dijkstra's algorithm
        # dict from (node,state) to length of shortest known path to the target
        # state
        distance = {}
        previous = {}
        INFINITY = 0x80000000
        for expnode in self.nodedict.itervalues():
            distance[expnode] = INFINITY
            previous[expnode] = None

        distance[self.initial] = 0
        worklist = list(self.nodedict.itervalues())
        while worklist:
            # we don't actually need to do a full sort each time, we could
            # just update the position of the item that changed
            worklist.sort(lambda en1, en2: distance[en1] - distance[en2])
            expnode = worklist[0]
            if expnode.node == dstnode and expnode.state == dststate:
                # We've found the target node:
                path = [expnode]
                while previous[expnode]:
                    path = [previous[expnode]] + path
                    expnode = previous[expnode]
                return path
            worklist = worklist[1:]
            if distance[expnode] == INFINITY:
                # disjoint
                break
            for edge in self.edges:
                if edge.srcexpnode.node == expnode.node and edge.srcexpnode.state == expnode.state:
                    alt = distance[expnode] + 1
                    if alt < distance[edge.dstexpnode]:
                        distance[edge.dstexpnode] = alt
                        previous[edge.dstexpnode] = expnode

class ExplodedNode:
    def __init__(self, node, state):
        self.node = node
        self.state = state

    def __repr__(self):
        return 'ExplodedNode(%r, %r)' % (self.node, self.state)

class ExplodedEdge:
    def __init__(self, srcexpnode, dstexpnode):
        self.srcexpnode = srcexpnode
        self.dstexpnode = dstexpnode

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
            if (loc, state) not in expgraph.nodedict:
                expnode = expgraph.lazily_add_node(loc, state)
                worklist.append(expnode)
            else:
                # (won't do anything)
                expnode = expgraph.lazily_add_node(loc, state)
            return expnode
        srcexpnode = worklist.pop()
        srcloc = srcexpnode.node
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
                                    if isinstance(outcome, sm.parser.BooleanOutcome):
                                        if 0:
                                            print(edge.true_value)
                                            print(edge.false_value)
                                            print(outcome.guard)
                                        if edge.true_value and outcome.guard:
                                            handle_outcome(outcome.outcome)
                                        if edge.false_value and not outcome.guard:
                                            handle_outcome(outcome.outcome)
                                    elif isinstance(outcome, sm.parser.TransitionTo):
                                        # print('transition to %s' % outcome.state)
                                        dststate = outcome.state
                                        dstexpnode = lazily_add_node(dstloc, dststate)
                                        expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode)
                                    elif isinstance(outcome, sm.parser.PythonOutcome):
                                        ctxt.srcloc = srcloc
                                        outcome.run(ctxt, expgraph, srcloc, srcstate)
                                    else:
                                        print(outcome)
                                        raise UnknownOutcome(outcome)
                                handle_outcome(outcome)
                            matches.append(pr)
            if not matches:
                dstexpnode = lazily_add_node(dstloc, srcstate)
                expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode)
    return expgraph

def solve(fun, ctxt):
    if 0:
        solver = Solver(fun, ctxt)
        solver.solve()

    if 1:
        expgraph = make_exploded_graph(fun, ctxt)
        if 0:
            # Debug: view the exploded graph:
            dot = expgraph.to_dot()
            # print(dot)
            invoke_dot(dot, fun.decl.name)

class Context:
    # An sm.parser.Sm in contect, with a mapping from its vars to gcc.VarDecl
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

