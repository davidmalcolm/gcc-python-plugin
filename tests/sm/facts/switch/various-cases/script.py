# -*- coding: utf-8 -*-
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

from sm import main
from sm.parser import parse_file

def selftest(ctxt, solution):
    if 0:
        import sys
        solution.dump(sys.stderr)

    node = ctxt.find_call_of('marker_A')

    # Check that we know the constraints on i at each case label

    # Combination of case ranges: 0 ... 10 and 20 ... 30
    node = ctxt.find_call_of('marker_B')
    ctxt.assert_fact(node, 'i', '>=', 0)
    ctxt.assert_fact(node, 'i', '<=', 30)

    # Combination of case labels 0x42 and 42:
    node = ctxt.find_call_of('marker_C')
    ctxt.assert_fact(node, 'i', '>=', 42)
    ctxt.assert_fact(node, 'i', '<=', 0x42)

    # Single case labels 70:
    node = ctxt.find_call_of('marker_D')
    ctxt.assert_fact(node, 'i', '==', 70)

    # Case label 80 plus fallthrough of case label 70:
    node = ctxt.find_call_of('marker_E')
    # currently the fact-finder gives no information for the combination of
    # the two:
    ctxt.assert_no_facts(node)

    # "default" gives no information:
    node = ctxt.find_call_of('marker_F')
    ctxt.assert_no_facts(node)

    # Similarly, we have no information after control merges from all of
    # the cases:
    node = ctxt.find_call_of('marker_G')
    ctxt.assert_no_facts(node)


checker = parse_file('sm/checkers/malloc_checker.sm')
main([checker], selftest=selftest)
