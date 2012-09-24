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

from gccutils.dot import to_html

############################################################################
# Generic directed graphs
############################################################################
class Graph:
    def __init__(self):
        self.nodes = []
        self.edges = []

    def add_node(self, node):
        self.nodes.append(node)
        return node

    def add_edge(self, srcnode, dstnode, *args, **kwargs):
        e = self._make_edge(srcnode, dstnode, *args, **kwargs)
        self.edges.append(e)
        srcnode.succs.append(e)
        dstnode.preds.append(e)
        return e

    def _make_edge(self, srcnode, dstnode):
        return Edge(srcnode, dstnode)

    def to_dot(self, name, ctxt=None):
        result = 'digraph %s {\n' % name
        result += '  node [shape=box];\n'
        result += self._nodes_to_dot(ctxt)
        for edge in self.edges:
            result += ('    %s -> %s [label=<%s>];\n'
                       % (edge.srcnode.to_dot_id(),
                          edge.dstnode.to_dot_id(),
                          edge.to_dot_label(ctxt)))
        result += '}\n'
        return result

    def _nodes_to_dot(self, ctxt):
        result = ''
        for node in self.nodes:
            result += ('  %s [label=<%s>];\n'
                       % (node.to_dot_id(),
                          node.to_dot_label(ctxt)))
        return result

    def get_shortest_path(self, srcnode, dstnode):
        '''
        Locate the shortest path from the srcnode to the dstnode
        Return a list of Edge instances, or None if no such path exists
        '''
        # Dijkstra's algorithm
        # A dict giving for each node the length of the shortest known path
        # from srcnode to this node:
        distance = {}

        # A dict giving for each node the previous node within that shortest
        # path:
        inedge = {}

        INFINITY = 0x80000000
        for node in self.nodes:
            distance[node] = INFINITY
            inedge[node] = None
        distance[srcnode] = 0

        worklist = list(self.nodes)
        while worklist:
            # we don't actually need to do a full sort each time, we could
            # just update the position of the item that changed
            worklist.sort(lambda node1, node2:
                              distance[node1] - distance[node2])
            node = worklist[0]
            if node == dstnode:
                # We've found the target node; build a path of the edges to
                # follow to get here:
                path = []
                while inedge[node]:
                    path = [inedge[node]] + path
                    node = inedge[node].srcnode
                return path
            worklist = worklist[1:]
            if distance[node] == INFINITY:
                # disjoint
                break
            for edge in node.succs:
                alt = distance[node] + 1
                if alt < distance[edge.dstnode]:
                    distance[edge.dstnode] = alt
                    inedge[edge.dstnode] = edge



class Node:
    def __init__(self):
        self.preds = []
        self.succs = []

    def to_dot_id(self):
        return '%s' % id(self)

    def to_dot_label(self, ctxt):
        return to_html(str(self))

class Edge:
    def __init__(self, srcnode, dstnode):
        self.srcnode = srcnode
        self.dstnode = dstnode

    def __repr__(self):
        return '%s(srcnode=%r, dstnode=%r)' % (self.__class__.__name__, self.srcnode, self.dstnode)

    def to_dot_label(self, ctxt):
        return ''

############################################################################
# A CFG, but with individual statements for nodes, rather than lumping them
# together within basic blocks
# It also has "empty" nodes i.e. those with no statements, to handle
# the empty BBs in the original CFG (entry and exit)
# FIXME: this doesn't yet cover PHI nodes...
############################################################################
class StmtGraph(Graph):
    def __init__(self, fun):
        Graph.__init__(self)
        self.entry = None
        self.exit = None
        # Mappings from gcc.BasicBlock to StmtNode so that we can wire up
        # the edges for the gcc.Edge:
        self.entry_of_bb = {}
        self.exit_of_bb = {}
        self.node_for_stmt = {}

        # 1st pass: create nodes and edges within BBs:
        for bb in fun.cfg.basic_blocks:
            if bb.gimple:
                lastnode = None
                for stmt in bb.gimple:
                    nextnode = self.add_node(StmtNode(fun, stmt))
                    self.node_for_stmt[stmt] = nextnode
                    if lastnode:
                        self.add_edge(lastnode, nextnode, None)
                    else:
                        self.entry_of_bb[bb] = nextnode
                    lastnode = nextnode
                self.exit_of_bb[bb] = lastnode
            else:
                if bb == fun.cfg.entry:
                    cls = EntryNode
                elif bb == fun.cfg.exit:
                    cls = ExitNode
                else:
                    assert 0
                node = self.add_node(cls(fun, None))
                self.entry_of_bb[bb] = node
                self.exit_of_bb[bb] = node
                if bb == fun.cfg.entry:
                    self.entry = node
                elif bb == fun.cfg.exit:
                    self.exit = node

        # 2nd pass: wire up the cross-BB edges:
        for bb in fun.cfg.basic_blocks:
            for edge in bb.succs:
                self.add_edge(self.exit_of_bb[bb],
                              self.entry_of_bb[edge.dest],
                              edge)

    def _make_edge(self, srcnode, dstnode, edge):
        return StmtEdge(srcnode, dstnode, edge)

class StmtNode(Node):
    def __init__(self, fun, stmt):
        Node.__init__(self)
        self.fun = fun
        self.stmt = stmt # can be None for empty BBs

    def __str__(self):
        return str(self.stmt)

class EntryNode(StmtNode):
    def __str__(self):
        return 'ENTRY %s' % self.fun.decl.name

class ExitNode(StmtNode):
    def __str__(self):
        return 'EXIT %s' % self.fun.decl.name

class StmtEdge(Edge):
    def __init__(self, srcnode, dstnode, cfgedge):
        Edge.__init__(self, srcnode, dstnode)
        self.cfgedge = cfgedge # will be None within a BB

    def to_dot_label(self, ctx):
        if self.cfgedge:
            if self.cfgedge.true_value:
                return 'true'
            elif self.cfgedge.false_value:
                return 'false'
        return ''

############################################################################
# Supergraph of all CFGs, built from each functions' StmtGraph.
# A graph in which the nodes wrap StmtNode
############################################################################
class Supergraph(Graph):
    def __init__(self):
        Graph.__init__(self)
        # 1st pass: locate interprocedural instances of gcc.GimpleCall
        # i.e. where both caller and callee are within the supergraph
        # (perhaps the same function)
        ipcalls = set()
        from gcc import get_callgraph_nodes
        for node in get_callgraph_nodes():
            fun = node.decl.function
            if fun:
                for edge in node.callees:
                    if edge.callee.decl.function:
                        ipcalls.add(edge.call_stmt)

        # 2nd pass: construct a StmtGraph for each function in the callgraph
        # and add nodes and edges to "self" wrapping the nodes and edges
        # within each StmtGraph:
        self.stmtg_for_fun = {}
        for node in get_callgraph_nodes():
            fun = node.decl.function
            if fun:
                stmtg = StmtGraph(fun)
                self.stmtg_for_fun[fun] = stmtg
                # Clone the stmtg nodes and edges into the Supergraph:
                stmtg.snode_for_stmtnode = {}
                for node in stmtg.nodes:
                    stmtg.snode_for_stmtnode[node] = self.add_node(SupergraphNode(node))
                for edge in stmtg.edges:
                    # FIXME: mark the intraprocedural call edges
                    edgecls = SupergraphEdge
                    if edge.srcnode.stmt in ipcalls:
                        edgecls = CallToReturnSiteEdge
                    sedge = self.add_edge(
                        stmtg.snode_for_stmtnode[edge.srcnode],
                        stmtg.snode_for_stmtnode[edge.dstnode],
                        edgecls,
                        edge)

        # 3rd pass: add the interprocedural edges (call and return):
        for node in get_callgraph_nodes():
            fun = node.decl.function
            if fun:
                for edge in node.callees:
                    if edge.callee.decl.function:
                        calling_stmtg = self.stmtg_for_fun[fun]
                        called_stmtg = self.stmtg_for_fun[edge.callee.decl.function]

                        calling_stmtnode = calling_stmtg.node_for_stmt[edge.call_stmt]
                        assert calling_stmtnode

                        entry_stmtnode = called_stmtg.entry
                        assert entry_stmtnode

                        exit_stmtnode = called_stmtg.exit
                        assert exit_stmtnode

                        returnsite_stmtnode = calling_stmtnode.succs[0].dstnode
                        assert returnsite_stmtnode

                        sedge_call = self.add_edge(
                            calling_stmtg.snode_for_stmtnode[calling_stmtnode],
                            called_stmtg.snode_for_stmtnode[entry_stmtnode],
                            CallToStart,
                            None)
                        sedge_return = self.add_edge(
                            called_stmtg.snode_for_stmtnode[exit_stmtnode],
                            calling_stmtg.snode_for_stmtnode[returnsite_stmtnode],
                            ExitToReturnSite,
                            None)

    def _make_edge(self, srcnode, dstnode, cls, edge):
        return cls(srcnode, dstnode, edge)

    def _nodes_to_dot(self, ctxt):
        # group the nodes into subgraphs within their original
        # functions
        result = ''
        for fun in self.stmtg_for_fun:
            result += '  subgraph cluster_%s {\n' % fun.decl.name
            stmtg = self.stmtg_for_fun[fun]
            for node in stmtg.nodes:
                snode = stmtg.snode_for_stmtnode[node]
                result += ('    %s [label=<%s>];\n'
                           % (snode.to_dot_id(),
                              snode.to_dot_label(ctxt)))
            result += '  }\n'
        return result

class SupergraphNode(Node):
    """
    A node in the supergraph, wrapping a StmtNode
    """
    def __init__(self, innernode):
        Node.__init__(self)
        self.innernode = innernode

    def __str__(self):
        return str(self.innernode)

class SupergraphEdge(Edge):
    """
    An edge in the supergraph, wrapping a StmtEdge,
    or None for the intraprocedual edges for function call/return
    """
    def __init__(self, srcnode, dstnode, inneredge):
        Edge.__init__(self, srcnode, dstnode)
        self.inneredge = inneredge

    def to_dot_label(self, ctxt):
        return self.inneredge.to_dot_label(ctxt)

class CallToReturnSiteEdge(SupergraphEdge):
    """
    The intraprocedural edge for a function call, from
    the gcc.GimpleCall to the next statement
    """
    def to_dot_label(self, ctxt):
        return 'within function'

class CallToStart(SupergraphEdge):
    """
    The interprocedural edge for the start of a function call: from
    the gcc.GimpleCall to the entry node of the callee
    """
    def to_dot_label(self, ctxt):
        return 'call'

class ExitToReturnSite(SupergraphEdge):
    """
    The interprocedural edge for the end of a function call: from
    the exit node of the callee to the successor node of the
    gcc.GimpleCall within the caller
    """
    def to_dot_label(self, ctxt):
        return 'return'
