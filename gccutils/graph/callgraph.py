#   Copyright 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2013 Red Hat, Inc.
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

from gccutils.graph import Graph, Node, Edge

############################################################################
# The callgraph, built as a Graph instance
############################################################################
class Callgraph(Graph):
    __slots__ = ('node_for_innernode', 'edge_for_inneredge',)

    def __init__(self):
        Graph.__init__(self)
        self.node_for_innernode = {}
        self.edge_for_inneredge = {}

        # Build wrapper nodes:
        for innernode in gcc.get_callgraph_nodes():
            node = CallgraphNode(innernode)
            self.node_for_innernode[innernode] = node
            self.add_node(node)

        # Build wrapper edges:
        for innernode in gcc.get_callgraph_nodes():
            for inneredge in innernode.callees:
                srcnode = self.node_for_innernode[inneredge.caller]
                dstnode = self.node_for_innernode[inneredge.callee]
                edge = self.add_edge(srcnode, dstnode, inneredge)
                self.edge_for_inneredge[inneredge] = edge

    def _make_edge(self, srcnode, dstnode, inneredge):
        return CallgraphEdge(srcnode, dstnode, inneredge)

class CallgraphNode(Node):
    __slots__ = ('innernode', )

    def __init__(self, innernode):
        Node.__init__(self)
        self.innernode = innernode

class CallgraphEdge(Edge):
    __slots__ = ('inneredge', )

    def __init__(self, srcnode, dstnode, inneredge):
        Edge.__init__(self, srcnode, dstnode)
        self.inneredge = inneredge
