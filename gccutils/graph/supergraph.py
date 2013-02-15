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

from gccutils.graph import Graph, Node, Edge, Subgraph
from gccutils.graph.stmtgraph import StmtGraph

############################################################################
# Supergraph of all CFGs, built from each functions' StmtGraph.
# A graph in which the nodes wrap StmtNode
############################################################################
class Supergraph(Graph):
    __slots__ = ('supernode_for_stmtnode',
                 'stmtg_for_fun',
                 'fake_entry_node')

    def __init__(self, split_phi_nodes, add_fake_entry_node):
        Graph.__init__(self)
        self.supernode_for_stmtnode = {}
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
                stmtg = StmtGraph(fun, split_phi_nodes)
                self.stmtg_for_fun[fun] = stmtg
                # Clone the stmtg nodes and edges into the Supergraph:
                stmtg.supernode_for_stmtnode = {}
                for node in stmtg.nodes:
                    if node.stmt in ipcalls:
                        # These nodes will have two supernodes, a CallNode
                        # and a ReturnNode:
                        callnode = self.add_node(CallNode(node, stmtg))
                        returnnode = self.add_node(ReturnNode(node, stmtg))
                        callnode.returnnode = returnnode
                        returnnode.callnode = callnode
                        stmtg.supernode_for_stmtnode[node] = (callnode, returnnode)
                        self.add_edge(
                            callnode, returnnode,
                            CallToReturnSiteEdge, None)
                    else:
                        stmtg.supernode_for_stmtnode[node] = \
                            self.add_node(SupergraphNode(node, stmtg))
                for edge in stmtg.edges:
                    if edge.srcnode.stmt in ipcalls:
                        # Begin the superedge from the ReturnNode:
                        srcsupernode = stmtg.supernode_for_stmtnode[edge.srcnode][1]
                    else:
                        srcsupernode = stmtg.supernode_for_stmtnode[edge.srcnode]
                    if edge.dstnode.stmt in ipcalls:
                        # End the superedge at the CallNode:
                        dstsupernode = stmtg.supernode_for_stmtnode[edge.dstnode][0]
                    else:
                        dstsupernode = stmtg.supernode_for_stmtnode[edge.dstnode]
                    superedge = self.add_edge(srcsupernode, dstsupernode,
                                              SupergraphEdge, edge)

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

                        superedge_call = self.add_edge(
                            calling_stmtg.supernode_for_stmtnode[calling_stmtnode][0],
                            called_stmtg.supernode_for_stmtnode[entry_stmtnode],
                            CallToStart,
                            None)
                        superedge_return = self.add_edge(
                            called_stmtg.supernode_for_stmtnode[exit_stmtnode],
                            calling_stmtg.supernode_for_stmtnode[calling_stmtnode][1],
                            ExitToReturnSite,
                            None)
                        superedge_return.calling_stmtnode = calling_stmtnode

        # 4th pass: create fake entry node:
        if not add_fake_entry_node:
            self.fake_entry_node = None
            return

        self.fake_entry_node = self.add_node(FakeEntryNode(None, None))
        """
	/* At file scope, the presence of a `static' or `register' storage
	   class specifier, or the absence of all storage class specifiers
	   makes this declaration a definition (perhaps tentative).  Also,
	   the absence of `static' makes it public.  */
	if (current_scope == file_scope)
	  {
	    TREE_PUBLIC (decl) = storage_class != csc_static;
	    TREE_STATIC (decl) = !extern_ref;
	  }
          """
        # For now, assume all non-static functions are possible entrypoints:
        for fun in self.stmtg_for_fun:
            # Only for non-static functions:
            if fun.decl.is_public:
                stmtg = self.stmtg_for_fun[fun]
                self.add_edge(self.fake_entry_node,
                              stmtg.supernode_for_stmtnode[stmtg.entry],
                              FakeEntryEdge,
                              None)

    def add_node(self, supernode):
        Graph.add_node(self, supernode)
        # Keep track of mapping from stmtnode -> supernode
        self.supernode_for_stmtnode[supernode.innernode] = supernode
        return supernode

    def _make_edge(self, srcnode, dstnode, cls, edge):
        return cls(srcnode, dstnode, edge)

    def get_entry_nodes(self):
        if self.fake_entry_node:
            yield self.fake_entry_node

    def get_functions(self):
        for fun in self.stmtg_for_fun:
            yield fun

class SupergraphNode(Node):
    """
    A node in the supergraph, wrapping a StmtNode
    """
    __slots__ = ('innernode', 'stmtg')

    def __init__(self, innernode, stmtg):
        Node.__init__(self)
        self.innernode = innernode
        self.stmtg = stmtg

    def to_dot_html(self, ctxt):
        return self.innernode.to_dot_html(ctxt)

    def __str__(self):
        return str(self.innernode)

    def __repr__(self):
        return 'SupergraphNode(%r)' % self.innernode

    @property
    def supergraphnode(self):
        return self

    @property
    def stmtnode(self):
        return self.innernode

    @property
    def stmt(self):
        if self.innernode:
            return self.innernode.get_stmt()

    def get_stmt(self):
        if self.innernode:
            return self.innernode.get_stmt()

    def get_gcc_loc(self):
        if self.innernode:
            return self.innernode.get_gcc_loc()

    def get_subgraph_path(self, ctxt):
        if self.stmtg:
            func = self.stmtg.fun
            filename = func.start.file
            funcname = func.decl.name
            return (Subgraph(filename, filename),
                    Subgraph(funcname, funcname), )
        return ()

    @property
    def function(self):
        """
        Get the gcc.Function for this node
        """
        if self.stmtg:
            return self.stmtg.fun

class CallNode(SupergraphNode):
    """
    A first node for a gcc.GimpleCall, representing the invocation of the
    function.
    It has the same stmt (the gcc.GimpleCall) as the ReturnNode
    """
    __slots__ = ('returnnode', # the corresponding ReturnNode
                 )

class ReturnNode(SupergraphNode):
    """
    A second node for a gcc.GimpleCall, representing the assignment of the
    return value from the completed call into the LHS.
    It has the same stmt (the gcc.GimpleCall) as the CallNode
    """
    __slots__ = ('callnode', # the corresponding CallNode
                 )

class FakeEntryNode(SupergraphNode):
    """
    Fake entry node which links to all externally-visible entry nodes, so
    that a supergraph can have a unique entrypoint.

    It represents "the outside world" when analyzing the supergraph of a
    shared library.
    """
    __slots__ = ()

    def __str__(self):
        return 'ALL ENTRYPOINTS'

    def __repr__(self):
        return 'FakeEntryNode'

    def to_dot_html(self, ctxt):
        from gccutils.dot import Text
        return Text('ALL ENTRYPOINTS')

class SupergraphEdge(Edge):
    """
    An edge in the supergraph, wrapping a StmtEdge,
    or None for the intraprocedual edges for function call/return
    """
    __slots__ = ('inneredge', )

    def __init__(self, srcnode, dstnode, inneredge):
        Edge.__init__(self, srcnode, dstnode)
        self.inneredge = inneredge

    def to_dot_label(self, ctxt):
        if self.inneredge:
            return self.inneredge.to_dot_label(ctxt)

    @property
    def true_value(self):
        if self.inneredge:
            return self.inneredge.true_value

    @property
    def false_value(self):
        if self.inneredge:
            return self.inneredge.false_value

    @property
    def stmtedge(self):
        return self.inneredge

class CallToReturnSiteEdge(SupergraphEdge):
    """
    The intraprocedural edge for a function call, from
    the gcc.GimpleCall to the next statement
    """
    __slots__ = ()

    def to_dot_label(self, ctxt):
        return 'within function'

    def to_dot_attrs(self, ctxt):
        return ' penwidth=2'

class CallToStart(SupergraphEdge):
    """
    The interprocedural edge for the start of a function call: from
    the gcc.GimpleCall to the entry node of the callee
    """
    __slots__ = ()

    def to_dot_label(self, ctxt):
        return 'call of %s' % self.dstnode.function.decl.name

    def to_dot_attrs(self, ctxt):
        #return ' constraint=false, style=dotted'
        return ' style=dotted'

class ExitToReturnSite(SupergraphEdge):
    """
    The interprocedural edge for the end of a function call: from
    the exit node of the callee to the successor node of the
    gcc.GimpleCall within the caller
    """
    __slots__ = ('calling_stmtnode', )

    def to_dot_label(self, ctxt):
        return 'return to %s' % self.dstnode.function.decl.name

    def to_dot_attrs(self, ctxt):
        #return ' constraint=false, style=dotted'
        return ' style=dotted'

class FakeEntryEdge(SupergraphEdge):
    """
    Fake edge from the FakeEntryNode to one of the entrypoints.

    This represents a call "from outside" the scope of the supergraph
    (e.g. for analyzing a library)
    """
    __slots__ = ()

    def to_dot_label(self, ctxt):
        return 'external call'
