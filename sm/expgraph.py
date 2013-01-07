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

from gccutils.dot import Table, Tr, Td, Text, Br, Font
from gccutils.graph import Graph, Node, Edge

from sm.solver import StatesForNode, ENABLE_LOG
from sm.utils import stateset_to_str, equivcls_to_str

class ExplodedGraph(Graph):
    """
    An exploded Supergraph where (equivcls, state) information has been
    added to each node, so that are multiple nodes representing each inner
    node, and the edges represent the valid state changes.

    Within each node, we have the subset of state for when:

        (equivcls == state)

    Hence for the node with states:

       {v1, v2} : {stateA, stateB}, {v3} : {stateC, stateD, stateE}

    there will be 5 StatewiseExplodedNodes, for:
        {v1, v2}: stateA
        {v1, v2}: stateB
        {v3}: stateC
        {v3}: stateD
        {v3}: stateE
    to ensure that we have an ExplodedNode for each possible equivcls:state
    pairing, whilst avoiding visiting all possible combinations.

    As a special case we don't split nodes which have just a single possible
    state for each equivcls, and use a SoloExplodedNode to represent this
    case

    Every edge is also labelled with the sm.checker.Match (if any) that
    causes it.
    """
    __slots__ = ('ctxt', 'innergraph',
                 'expnode_for_triple',
                 'expnodes_for_innernode')

    def __init__(self, ctxt, innergraph):
        Graph.__init__(self)
        self.ctxt = ctxt
        self.innergraph = innergraph

        # dict from (SupergraphNode, equivcls, state) to ExplodedNode:
        self.expnode_for_triple = {}

        # dict from SupergraphNode to set of ExplodedNode:
        self.expnodes_for_innernode = {}

    def add_node(self, expnode):
        """
        key = (expnode.innernode, expnode.equivcls, expnode.state)
        assert key not in self.expnode_for_triple
        self.expnode_for_triple[key] = expnode
        """
        if expnode.innernode in self.expnodes_for_innernode:
            self.expnodes_for_innernode[expnode.innernode].add(expnode)
        else:
            self.expnodes_for_innernode[expnode.innernode] = set([expnode])
        return Graph.add_node(self, expnode)

    def get_entry_nodes(self):
        return [self.get_entry_node()]

    def get_entry_node(self):
        for expnode in self.expnodes_for_innernode[self.innergraph.fake_entry_node]:
            return expnode # there should be just one

    def get_expnode_with_state(self, innernode, equivcls, state):
        assert equivcls is not None
        assert state is not None

        for expnode in self.expnodes_for_innernode[innernode]:
            if state in expnode.states_subset._dict[equivcls]:
                return expnode

    def _make_edge(self, srcnode, dstnode, inneredge, match):
        return ExplodedEdge(srcnode, dstnode, inneredge, match)

class ExplodedNode(Node):
    __slots__ = ('innernode', 'states_subset', )

    def __init__(self, ctxt, innernode):
        Node.__init__(self)
        self.innernode = innernode
        # (the subclasses also set up self.states_subset)

    def to_dot_html(self, ctxt):
        inner = self.innernode.to_dot_html(self)
        table = Table(cellborder=1)

        tr = table.add_child(Tr())
        td = tr.add_child(Td(align='left'))
        td.add_child(self.get_title_dot_html(ctxt))

        tr = table.add_child(Tr())
        td = tr.add_child(Td(align='left'))
        td.add_child(Text('states_subset: %s'
                          % self.states_subset))
        if ctxt.facts_for_expnode:
            facts = ctxt.facts_for_expnode[self]
            if facts:
                for fact in facts.set_:
                    tr = table.add_child(Tr())
                    td = tr.add_child(Td(align='left'))
                    td.add_child(Text('FACT: %s' % (fact, )))
            else:
                tr = table.add_child(Tr())
                td = tr.add_child(Td(align='left'))
                td.add_child(Text('NO FACTS'))
        tr = table.add_child(Tr())
        td = tr.add_child(Td(align='left'))
        td.add_child(inner)
        return table

    @property
    def stmt(self):
        return self.innernode.stmt

    @property
    def supergraphnode(self):
        return self.innernode.supergraphnode

    @property
    def stmtnode(self):
        return self.innernode.supergraphnode.stmtnode

    def get_subgraph_path(self, ctxt):
        return self.innernode.get_subgraph_path(ctxt)

    def get_states_for_expr(self, ctxt, expr):
        return self.states_subset.get_states_for_expr(ctxt, expr)

class SoloExplodedNode(ExplodedNode):
    """
    A node within the ExplodedGraph in which the underlying node has only
    one possible combination of state variables
    """
    __slots__ = ()

    def __init__(self, ctxt, innernode):
        ExplodedNode.__init__(self, ctxt, innernode)
        self.states_subset = ctxt.states_for_node[self.innernode]

    def __repr__(self):
        return 'SoloExplodedNode(%r)' % (self.innernode)

    def get_title_dot_html(self, ctxt):
        return Text('%s' % self.__class__.__name__)

class StatewiseExplodedNode(ExplodedNode):
    """
    A node within the ExplodedGraph exploring the case that a particular
    equivcls has a particular state
    """
    __slots__ = ('equivcls', 'state')

    def __init__(self, ctxt, innernode, equivcls, state):
        ExplodedNode.__init__(self, ctxt, innernode)
        self.equivcls = equivcls
        self.state = state

        # Calculate states_subset, the StatesForNode comprising all possible
        # states for the underlying innernode, intersected with just those
        # in which the given equivcls has the given state:
        allstates = ctxt.states_for_node[self.innernode]
        assert self.equivcls in allstates._dict
        _dict = allstates._dict.copy()
        _dict[self.equivcls] = frozenset([self.state])
        self.states_subset = StatesForNode(self.innernode, _dict)

    def __repr__(self):
        return ('StatewiseExplodedNode(%r, %r, %r)'
                % (self.innernode, self.equivcls, self.state))

    def get_title_dot_html(self, ctxt):
        return Text('%s: %s=%s '
                    % (self.__class__.__name__,
                       equivcls_to_str(self.equivcls),
                       self.state))

class ExplodedEdge(Edge):
    __slots__ = ('inneredge', 'match')

    def __init__(self, srcnode, dstnode, inneredge, match):
        Edge.__init__(self, srcnode, dstnode)
        self.inneredge = inneredge
        self.match = match

    def __hash__(self):
        return hash(self.srcnode) ^ hash(self.dstnode) ^ hash(self.inneredge)

    def __eq__(self, other):
        if isinstance(other, ExplodedEdge):
            if self.srcnode == other.srcnode:
                if self.dstnode == other.dstnode:
                    if self.inneredge == other.inneredge:
                        if self.match == other.match:
                            return True

    def to_dot_label(self, ctxt):
        result = self.inneredge.to_dot_label(ctxt)
        if self.match:
            desc = self.match.description(ctxt)
            result += (': ' if result else '') + desc
        return result

    @property
    def true_value(self):
        return self.inneredge.true_value

    @property
    def false_value(self):
        return self.inneredge.false_value

    @property
    def stmtedge(self):
        return self.inneredge.stmtedge

def build_exploded_graph(ctxt):
    expgraph = ExplodedGraph(ctxt, ctxt.graph)
    solonodes = set()

    # Populate the expgraph with nodes for the various (equivcls, state)
    # pairs:
    for innernode in ctxt.graph.nodes:
        states_for_node = ctxt.states_for_node[innernode]
        if not states_for_node:
            # Unreachable node
            continue
        assert isinstance(states_for_node, StatesForNode)

        # Add exploded nodes for every equivcls that has multiple possible
        # states:
        expnodes = []
        for equivcls in states_for_node._dict:
            assert isinstance(equivcls, frozenset)
            states = states_for_node._dict[equivcls]
            if len(states) > 1:
                for state in states:
                    expnode = StatewiseExplodedNode(ctxt, innernode, equivcls, state)
                    expgraph.add_node(expnode)
                    expnodes.append(expnode)
        if not expnodes:
            # We have a node for which every equivcls has exactly one state;
            # add an exploded node representing this:
            expnode = SoloExplodedNode(ctxt, innernode)
            expgraph.add_node(expnode)
            solonodes.add(innernode)

    # Create edges within the exploded graph:
    for i, srcexpnode in enumerate(expgraph.nodes):
        if i % 100 == 0:
            ctxt.timing('iter %i; len(expgraph.nodes): %i len(expgraph.edges): %i',
                        i, len(expgraph.nodes), len(expgraph.edges))

        ctxt.log('srcexpnode: %s', srcexpnode)
        with ctxt.indent():
            # Get the subset of state at this node:
            srcvalue = srcexpnode.states_subset
            if srcvalue is None:
                continue

            ctxt.log('srcvalue (subset): %s', srcvalue)
            for inneredge in srcexpnode.innernode.succs:
                ctxt.log('inneredge: %s', inneredge)
                with ctxt.indent():
                    # Rerun the state propagation for the state subset for the
                    # given edge to get some state subset for the dstnode
                    # (which might be the whole of the state set):
                    dstnode = inneredge.dstnode
                    dstvalue, match = StatesForNode.get_edge_value(ctxt, srcvalue, inneredge)
                    if ENABLE_LOG:
                        ctxt.log('dstvalue (subset): %s', dstvalue)
                        ctxt.log('match: %s', match)
                        ctxt.log('states for dstnode: %s', ctxt.states_for_node[dstnode])

                    if dstvalue is None:
                        continue

                    # Wire up edges accordingly within the ExplodedGraph:
                    dstexpnodes = expgraph.expnodes_for_innernode[dstnode]
                    if dstnode in solonodes:
                        assert len(dstexpnodes) == 1
                        for dstexpnode in dstexpnodes:
                            # (there will just be one)
                            expgraph.add_edge(srcexpnode, dstexpnode, inneredge, match)
                            ctxt.log('added edge to solo node')
                    else:
                        for dstexpnode in dstexpnodes:
                            if ENABLE_LOG:
                                ctxt.log('dstexpnode: equivcls: %s state: %s states_subset: %s',
                                         equivcls_to_str(dstexpnode.equivcls),
                                         dstexpnode.state,
                                         dstexpnode.states_subset) # stateset_to_str(dstexpnode.states_subset))
                            if dstvalue.is_subset_of(dstexpnode.states_subset):
                                expgraph.add_edge(srcexpnode, dstexpnode, inneredge, match)
                                ctxt.log('(added edge for ^^^)')

    return expgraph
