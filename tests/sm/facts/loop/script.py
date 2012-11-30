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

    # Check that we know the constraints on i within the loop:
    node = ctxt.find_call_of('marker_B')
    ctxt.assert_fact(node, 'i', '<=', 255)
    ctxt.assert_not_fact(node, 'i', '==', 0)

    # Check that we know the constraints on i after the loop:
    node = ctxt.find_call_of('marker_C')
    ctxt.assert_fact(node, 'i', '>', 255)

    # TODO: we don't yet do interval analysis, so we can't prove
    # that (i == 256) after the loop.

checker = parse_file('sm/checkers/malloc_checker.sm')
main([checker], selftest=selftest)
