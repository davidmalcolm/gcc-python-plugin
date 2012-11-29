# -*- coding: utf-8 -*-
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

# Note: the line diagrams in the comments use the
# Unicode "Box Drawing" characters:
#   ─ : U+2500 BOX DRAWINGS LIGHT HORIZONTAL
#   │ : U+2502 BOX DRAWINGS LIGHT VERTICAL
#   ┐ : U+2510 BOX DRAWINGS LIGHT DOWN AND LEFT
#   └ : U+2514 BOX DRAWINGS LIGHT UP AND RIGHT
#   ┘ : U+2518 BOX DRAWINGS LIGHT UP AND LEFT
# (the arrows are the greater than/less than and the letters A and V)

import unittest

from gccutils.graph import Graph, Node, Edge

class NamedNode(Node):
    def __init__(self, name=None):
        Node.__init__(self)
        self.name = name

    def __str__(self):
        if self.name:
            return self.name
        return 'node'

    def __repr__(self):
        return '%r' % self.name

def make_trivial_graph():
    """
    Construct a trivial graph:
       a ─> b
    """
    g = Graph()
    a = g.add_node(NamedNode('a'))
    b = g.add_node(NamedNode('b'))
    ab = g.add_edge(a, b)
    return g, a, b, ab

def add_long_path(g, length):
    """
    Construct a path of the form:
        first -> n0 -> n1 -> .... -> last
    where there are "length" edges
    """
    first = g.add_node(Node())
    last = first
    cur = first
    for i in range(length):
        last = g.add_node(Node())
        g.add_edge(cur, last)
        cur = last
    return first, last

def add_cycle(g, length):
    """
    Construct a cycle of the form
        first ─> n0 ─> n1 ─> ... ─> nN ┐
          A                            │
          └────────────────────────────┘
    where there are "length" edges
    """
    assert length > 0
    first, last = add_long_path(g, length - 1)
    g.add_edge(last, first)
    return first

class GraphTests(unittest.TestCase):
    def test_to_dot(self):
        g, a, b, ab = make_trivial_graph()
        dot = g.to_dot('example')

    def test_long_path(self):
        LENGTH = 1000
        g = Graph()
        first, last = add_long_path(g, LENGTH)
        self.assertEqual(len(g.edges), LENGTH)
        self.assertEqual(len(g.nodes), LENGTH + 1)
        dot = g.to_dot('example')

    def test_cycle(self):
        LENGTH = 5
        g = Graph()
        first = add_cycle(g, LENGTH)
        self.assertEqual(len(g.edges), LENGTH)
        self.assertEqual(len(g.nodes), LENGTH)
        dot = g.to_dot('example')

class PathfindingTests(unittest.TestCase):
    def test_no_path(self):
        g = Graph()
        a = g.add_node(Node())
        b = g.add_node(Node())
        # no edges between them
        path = g.get_shortest_path(a, b)
        self.assertEqual(path, []) # FIXME: shouldn't this be None?

    def test_trivial_path(self):
        g, a, b, ab = make_trivial_graph()
        path = g.get_shortest_path(a, b)
        self.assertEqual(path, [ab])

    def test_long_path(self):
        # Verify that get_shortest_path() can handle reasonably-sized graphs:
        #LENGTH = 100
        LENGTH = 10000
        g = Graph()
        first, last = add_long_path(g, LENGTH)
        path = g.get_shortest_path(first, last)
        self.assertEqual(len(path), LENGTH)
        self.assertEqual(path[0].srcnode, first)
        self.assertEqual(path[-1].dstnode, last)

    def test_cycles(self):
        LENGTH = 5
        g = Graph()
        a = add_cycle(g, LENGTH)
        b = add_cycle(g, LENGTH)
        c = add_cycle(g, LENGTH)
        ab = g.add_edge(a, b)
        bc = g.add_edge(b, c)
        path = g.get_shortest_path(a, c)
        self.assertEqual(len(path), 2)
        p0, p1 = path
        self.assertEqual(p0, ab)
        self.assertEqual(p1, bc)

    def test_fork(self):
        # Verify that it figures out the shortest path for:
        #  a ─> b─┬─> c ─> d ─┬─> f
        #         └─> e ──────┘
        g, a, b, ab = make_trivial_graph()

        c = g.add_node(NamedNode('c'))
        bc = g.add_edge(b, c)

        d = g.add_node(NamedNode('d'))
        cd = g.add_edge(c, d)

        e = g.add_node(NamedNode('e'))
        be = g.add_edge(b, e)

        f = g.add_node(NamedNode('f'))
        df = g.add_edge(d, f)
        ef = g.add_edge(e, f)

        path = g.get_shortest_path(a, f)
        self.assertEqual(len(path), 3)
        p0, p1, p2 = path
        self.assertEqual(p0, ab)
        self.assertEqual(p1, be)
        self.assertEqual(p2, ef)

import sys
sys.argv = ['foo', '-v']

unittest.main()
