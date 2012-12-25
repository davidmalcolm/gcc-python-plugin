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
class Graph(object):
    __slots__ = ('nodes', 'edges')

    def __init__(self):
        self.nodes = set()
        self.edges = set()

    def add_node(self, node):
        self.nodes.add(node)
        return node

    def add_edge(self, srcnode, dstnode, *args, **kwargs):
        assert isinstance(srcnode, Node)
        assert isinstance(dstnode, Node)
        e = self._make_edge(srcnode, dstnode, *args, **kwargs)
        self.edges.add(e)
        srcnode.succs.add(e)
        dstnode.preds.add(e)
        return e

    def _make_edge(self, srcnode, dstnode):
        return Edge(srcnode, dstnode)

    def remove_node(self, node):
        if node not in self.nodes:
            return 0
        self.nodes.remove(node)
        victims = 1
        for edge in list(node.succs):
            victims += self.remove_edge(edge)
        for edge in list(node.preds):
            victims += self.remove_edge(edge)
        return victims

    def remove_edge(self, edge):
        if edge not in self.edges:
            return 0
        self.edges.remove(edge)
        edge.srcnode.succs.remove(edge)
        edge.dstnode.preds.remove(edge)
        victims = 0
        if not edge.dstnode.preds:
            # We removed last inedge: recurse
            if edge.dstnode in self.nodes:
                victims += self.remove_node(edge.dstnode)
        return victims

    def to_dot(self, name, ctxt=None):
        result = 'digraph %s {\n' % name
        result += '  node [shape=box];\n'
        result += self._nodes_to_dot(ctxt)
        result += self._edges_to_dot(ctxt)
        result += '}\n'
        return result

    def _nodes_to_dot(self, ctxt):
        # A subgraph path is a tuple of Subgraph instances

        from pprint import pprint

        # 1st pass: get the subgraph path for every node
        # This is a dict from subgraph path to set of nodes:
        subgraph_paths = {}
        for node in self.nodes:
            subgraph_path = node.get_subgraph_path(ctxt)
            assert isinstance(subgraph_path, tuple)
            if 0:
                print('node: %s' % node)
                print('subgraph_path: %s' % (subgraph_path, ))
            if subgraph_path in subgraph_paths:
                subgraph_paths[subgraph_path].add(node)
            else:
                subgraph_paths[subgraph_path] = set([node])

        if 0:
            print('subgraph_paths:')
            pprint(subgraph_paths)

        # 2nd pass: construct a tree of subgraphs:
        # dict from subgraph path (parent) to set of subgraph paths
        # (immediate children):
        child_paths = {}
        # sort the paths, so that they are in order of increasing
        # length:
        for path in sorted(subgraph_paths.keys()):
            if path:
                for i in range(len(path) + 1):
                    subpath = path[0:i]
                    if 0:
                        print('subpath: %s' % (subpath, ))
                    if subpath:
                        parent = subpath[0:-1]
                        if parent in child_paths:
                            child_paths[parent].add(subpath)
                        else:
                            child_paths[parent] = set([subpath])
        if 0:
            print('child_paths:')
            pprint(child_paths)

        # 3rd pass: recursively render the subgraph paths:
        def render_subgraph_path(subgraph_path, indent):
            def _indent():
                return ' ' * indent
            result = ''
            if subgraph_path:
                result += ('%ssubgraph cluster_%s {\n'
                           % (_indent(), subgraph_path[-1].id))
                indent += 2
                result += ('%slabel = "%s";\n'
                           % (_indent(), subgraph_path[-1].label))

            for node in subgraph_paths.get(subgraph_path, set()):
                result += ('%s%s [label=<%s>];\n'
                           % (_indent(),
                              node.to_dot_id(),
                              node.to_dot_label(ctxt)))
            # Recurse:
            for child_path in child_paths.get(subgraph_path, set()):
                result += render_subgraph_path(child_path, indent)

            if subgraph_path:
                indent -= 2
                result += '%s}\n' % _indent()
            return result

        return render_subgraph_path( (), 2)

    def _edges_to_dot(self, ctxt):
        result = ''
        for edge in self.edges:
            result += ('    %s -> %s [label=<%s>%s];\n'
                       % (edge.srcnode.to_dot_id(),
                          edge.dstnode.to_dot_id(),
                          edge.to_dot_label(ctxt),
                          edge.to_dot_attrs(ctxt)))
        return result

    def topologically_sorted_nodes(self):
        from gccutils import topological_sort
        def get_srcs(node):
            for pred in node.preds:
                yield pred.srcnode
        def get_dsts(node):
            for succ in node.succs:
                yield succ.dstnode
        return topological_sort(self.nodes,
                                get_srcs,
                                get_dsts)

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

        # We use a heapq to keep the nodes sorted by distance
        # The items in the heapq are lists of the form:
        #    [distance_to_node, node, is_live)
        # The first entry in the list ensures that the heapq is sorted
        # into the order needed for Dijkstra's algorithm
        #
        # Since we can't change the priority of items within a heapq,
        # whenever we need to update the distance we mark the existing
        # item as dead (setting the is_live boolean to False), and add a
        # new entry with the correct value; we ignore dead items during
        # the iteration
        #
        # This gets the time taken for a simple 10000 node graph down to
        # ~3 seconds, compared to minutes/hours.
        from heapq import heapify, heappop, heappush
        item_for_node = {}
        for node in self.nodes:
            item_for_node[node] = [distance[node], node, True]

        worklist = list(item_for_node.values())
        heapify(worklist)
        while worklist:
            def get_next():
                while 1:
                    if not worklist:
                        return None
                    disttonode, node, islive = heappop(worklist)
                    if islive:
                        return node
            node = get_next()
            if node is None:
                # disjoint
                break
            if node == dstnode:
                # We've found the target node; build a path of the edges to
                # follow to get here:
                path = []
                while inedge[node]:
                    path = [inedge[node]] + path
                    node = inedge[node].srcnode
                return path
            if distance[node] == INFINITY:
                # disjoint
                break
            for edge in node.succs:
                alt = distance[node] + 1
                if alt < distance[edge.dstnode]:
                    distance[edge.dstnode] = alt
                    # Changing the distance of edge.dstnode requires us to
                    # update the heapq:
                    # Mark the existing item as dead:
                    item_for_node[edge.dstnode][2] = False
                    # Create a new itemwith the new distance:
                    newitem = [alt, edge.dstnode, True]
                    item_for_node[edge.dstnode] = newitem
                    heappush(worklist, newitem)
                    inedge[edge.dstnode] = edge
        return None


class Node(object):
    __slots__ = ('preds', 'succs')

    def __init__(self):
        self.preds = set()
        self.succs = set()

    def to_dot_id(self):
        return '%s' % id(self)

    def to_dot_label(self, ctxt):
        if hasattr(ctxt, 'node_to_dot_html'):
            htmlnode = ctxt.node_to_dot_html(self)
        else:
            htmlnode = self.to_dot_html(ctxt)
        if htmlnode:
            return htmlnode.to_html()
        else:
            return to_html(str(self))

    def to_dot_html(self, ctxt):
        # Optionally, build a tree of gccutils.dot.Node
        return None

    def get_subgraph_path(self, ctxt):
        # Optionally, allow nodes to be partitioned into a tree of subgraphs
        # Return a tuple of Subgraph instances
        return ()

class Edge(object):
    __slots__ = ('srcnode', 'dstnode')

    def __init__(self, srcnode, dstnode):
        self.srcnode = srcnode
        self.dstnode = dstnode

    def __repr__(self):
        return '%s(srcnode=%r, dstnode=%r)' % (self.__class__.__name__, self.srcnode, self.dstnode)

    def __str__(self):
        return '%s -> %s' % (self.srcnode, self.dstnode)

    def to_dot_label(self, ctxt):
        return ''

    def to_dot_attrs(self, ctxt):
        return ''

class Subgraph(object):
    __slots__ = ('id', 'label')

    def __init__(self, id_, label):
        self.id = ''
        for ch in id_:
            if ch.isalnum():
                self.id += ch
            else:
                self.id += '_'
        self.label = label

    def __eq__(self, other):
        if self.id == other.id:
            if self.label == other.label:
                return True

    def __hash__(self):
        return hash(self.id) ^ hash(self.label)

    def __str__(self):
        return '(%r, %r)' % (self.id, self.label)

    def __repr__(self):
        return 'Subgraph(%r, %r)' % (self.id, self.label)
