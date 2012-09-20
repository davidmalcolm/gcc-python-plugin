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

# Generic directed graphs
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
        for node in self.nodes:
            result += ('  %s [label=<%s>];\n'
                       % (node.to_dot_id(),
                          node.to_dot_label(ctxt)))
        for edge in self.edges:
            result += ('    %s -> %s [label=<%s>];\n'
                       % (edge.srcnode.to_dot_id(),
                          edge.dstnode.to_dot_id(),
                          edge.to_dot_label(ctxt)))
        result += '}\n'
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
