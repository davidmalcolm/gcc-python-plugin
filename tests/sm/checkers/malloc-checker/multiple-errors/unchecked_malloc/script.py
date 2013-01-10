# -*- coding: utf-8 -*-
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

from sm import main
from sm.parser import parse_file

def selftest(ctxt, solution):
    if 0:
        import sys
        solution.dump(sys.stderr)

    node_call = ctxt.find_call_of('malloc')
    ssaname = node_call.stmt.lhs

    p = ctxt.find_var(node_call, 'p')
    node_write_to_p_i = ctxt.get_nodes().assigning_constant(1).one()
    ctxt.assert_statenames_for_expr(node_write_to_p_i, p,
                                    frozenset(['ptr.unchecked']))

    # It should now have given up, with the p in the "ptr.nonnull" state:
    node_write_to_p_j = ctxt.get_nodes().assigning_constant(2).one()
    ctxt.assert_statenames_for_expr(node_write_to_p_j, p,
                                    frozenset(['ptr.nonnull']))

    node_write_to_p_k = ctxt.get_nodes().assigning_constant(3).one()
    ctxt.assert_statenames_for_expr(node_write_to_p_k, p,
                                    frozenset(['ptr.nonnull']))


checker = parse_file('sm/checkers/malloc_checker.sm')
main([checker], selftest=selftest)
