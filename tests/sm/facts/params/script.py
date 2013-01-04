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

from sm import main, Options
from sm.parser import parse_file

def selftest(ctxt, solution):
    if 0:
        import sys
        solution.dump(sys.stderr)

    node = ctxt.find_call_of('marker_A')

    node = ctxt.find_call_of('marker_B')
    ctxt.assert_fact(node, 'i', '>', 4)

    # Within called_function(),
    # arg i was passed to param j:
    node = ctxt.find_call_of('marker_C')
    #ctxt.assert_fact(node, 'i', '>', 4)
    ctxt.assert_fact(node, 'j', '>', 4)

    node = ctxt.find_call_of('marker_D')
    #ctxt.assert_fact(node, 'i', '>', 4)
    ctxt.assert_fact(node, 'j', '>', 4)
    ctxt.assert_fact(node, 'k', '>', 3)

    # Back to test:
    # return value k was returned to i:
    node = ctxt.find_call_of('marker_E')
    ctxt.assert_fact(node, 'i', '>', 3)

    # After control merges, we have no information:
    node = ctxt.find_call_of('marker_F')
    ctxt.assert_no_facts(node)


checker = parse_file('sm/checkers/malloc_checker.sm')
main([checker], selftest=selftest)
