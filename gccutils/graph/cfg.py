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
# A CFG, built as a Graph instance
############################################################################
class CFG(Graph):
    __slots__ = ('fun', 'innercfg',
                 'node_for_innerbb', 'edge_for_inneredge',)

    def __init__(self, fun):
        Graph.__init__(self)
        self.fun = fun
        self.innercfg = fun.cfg
        self.node_for_innerbb = {}
        self.edge_for_inneredge = {}

        # Build wrapper nodes:
        for innerbb in self.innercfg.basic_blocks:
            bbnode = BasicBlock(innerbb)
            self.node_for_innerbb[innerbb] = bbnode
            self.add_node(bbnode)

        # Build wrapper edges:
        for innerbb in self.innercfg.basic_blocks:
            for inneredge in innerbb.succs:
                srcnode = self.node_for_innerbb[inneredge.src]
                dstnode = self.node_for_innerbb[inneredge.dest]
                edge = self.add_edge(srcnode, dstnode, inneredge)
                self.edge_for_inneredge[inneredge] = edge

    def _make_edge(self, srcnode, dstnode, inneredge):
        return CFGEdge(srcnode, dstnode, inneredge)

class BasicBlock(Node):
    __slots__ = ('innerbb', )

    def __init__(self, innerbb):
        Node.__init__(self)
        self.innerbb = innerbb

    @property
    def index(self):
        return self.innerbb.index

    @property
    def gimple(self):
        return self.innerbb.gimple

class CFGEdge(Edge):
    __slots__ = ('inneredge', )

    def __init__(self, srcnode, dstnode, inneredge):
        Edge.__init__(self, srcnode, dstnode)
        self.inneredge = inneredge
