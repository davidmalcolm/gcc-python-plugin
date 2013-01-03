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

import unittest

from sm.facts import Facts, Fact

def make_facts(factlist):
    f = Facts()
    f.set_ = set(factlist)
    return f

class FactsTests(unittest.TestCase):
    def test_str(self):
        f = make_facts([Fact('b', '==', 'c'),
                        Fact('a', '==', 'b')])
        self.assertEqual(str(f),
                         '(a == b && b == c)')

    def test_equivclasses(self):
        f = make_facts([Fact('a', '==', 'b'),
                        Fact('b', '==', 'c')])
        self.assertEqual(f.get_equiv_classes(),
                         frozenset([frozenset(['a', 'b', 'c'])]))

        f = make_facts([Fact('a', '==', 'b'),
                        Fact('c', '>', 0)])
        self.assertEqual(f.get_equiv_classes(),
                         frozenset([frozenset(['a', 'b'])]))

        f = make_facts([Fact('a', '==', 'b'),
                        Fact('c', '==', 0)])
        self.assertEqual(f.get_equiv_classes(),
                         frozenset([frozenset(['a', 'b']),
                                    frozenset(['c', 0])]))

        f = make_facts([Fact('a', '==', 'b'),
                        Fact('c', '==', 'd'),
                        Fact('c', '==', 'b')])
        self.assertEqual(f.get_equiv_classes(),
                         frozenset([frozenset(['a', 'b', 'c', 'd'])]))

        f = make_facts([Fact('a', '==', 'b'),
                        Fact('b', '==', 0),
                        Fact('b', '!=', 1)])
        self.assertEqual(f.get_equiv_classes(),
                         frozenset([frozenset(['a', 'b', 0])]))

    def test_aliases(self):
        f = make_facts([Fact('a', '==', 'b'),
                        Fact('b', '==', 'c')])
        self.assertEqual(f.get_aliases('a'),
                         frozenset(['a', 'b', 'c']))
        self.assertEqual(f.get_aliases('d'),
                         frozenset(['d']))

class FakeContext:
    def __init__(self, verbose=0):
        self.verbose = verbose
    def debug(self, msg, *args):
        if self.verbose:
            print(msg % args)

class IsPossibleTests(unittest.TestCase):
    def assertPossible(self, f):
        self.assertEqual(f.is_possible(FakeContext()), True)

    def assertNotPossible(self, f):
        self.assertEqual(f.is_possible(FakeContext()), False)

    def test_empty(self):
        f = make_facts([])
        self.assertPossible(f)

    def test_single_values(self):
        f = make_facts([Fact('a', '==', 'b'),
                        Fact('b', '==', 0)])
        self.assertPossible(f)

    def test_inconsistent_equalities(self):
        f = make_facts([Fact('a', '==', 'b'),
                        Fact('b', '==', 0),
                        Fact('b', '==', 1)])
        self.assertNotPossible(f)

    def test_inequalities(self):
        f = make_facts([Fact('b', '==', 0),
                        Fact('b', '!=', 1)])
        self.assertPossible(f)

        f = make_facts([Fact('b', '==', 0),
                        Fact('b', '!=', 0)])
        self.assertNotPossible(f)

        f = make_facts([Fact('b', '==', 0),
                        Fact('b', '>', 0)])
        self.assertNotPossible(f)


import sys
sys.argv = ['foo', '-v']

unittest.main()
