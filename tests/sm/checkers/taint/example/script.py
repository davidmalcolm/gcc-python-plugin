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

import gcc

from sm import main
from sm.parser import parse_file

def selftest(ctxt, solution):
    if 0:
        import sys
        solution.dump(sys.stderr)

    # Verify the various state transitions within "test3"

    # Verify that the:
    #    D.2837_3 = fread (&tmp, 260, 1, f_2(D));
    # transitions "tmp" from "x.start" to "x.tainted"
    node = ctxt.find_call_of('fread', within='test3')
    ctxt.assert_statenames_for_varname(node, 'tmp', {'x.start'})

    node = ctxt.get_successor(node)
    ctxt.assert_statenames_for_varname(node, 'tmp', {'x.tainted'})

    # Verify that the:
    #    if (D.n >= 0)
    # transitions "D.n" from "x.tainted" to "x.has_lb"
    node = ctxt.find_comparison_against(gcc.GeExpr, 0, within='test3')
    tempvar = node.stmt.lhs
    ctxt.assert_statenames_for_expr(node, tempvar, {'x.tainted'})

    node = ctxt.get_true_successor(node)
    ctxt.assert_statenames_for_expr(node, tempvar, {'x.has_lb'})

    # Verify that the:
    #    if (D.n <= 255)
    # transitions "D.n" from "x.has_lb" to "x.ok"
    node = ctxt.find_comparison_against(gcc.LeExpr, 255, within='test3')
    tempvar = node.stmt.lhs
    ctxt.assert_statenames_for_expr(node, tempvar, {'x.has_lb'})

    node = ctxt.get_true_successor(node)
    ctxt.assert_statenames_for_expr(node, tempvar, {'x.ok'})

    # Verify that it's within the same equivcls as "tmp.i"
    tmp_i = ctxt.get_expr_by_str(node, 'tmp.i')
    ctxt.assert_statenames_for_expr(node, tmp_i, {'x.ok'})

checker = parse_file('sm/checkers/taint.sm')
#print(checker)
dot = checker.to_dot('test_script')
#print(dot)
if 0:
    from gccutils import invoke_dot
    invoke_dot(dot)
main([checker], selftest=selftest)
