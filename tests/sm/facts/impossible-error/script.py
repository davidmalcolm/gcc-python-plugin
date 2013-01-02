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

    # Verify that we know flag != 0 at marker_A:
    node = ctxt.find_call_of('marker_A')
    ctxt.assert_fact(node, 'flag', '!=', 0)

    # We should also know that ptr is non-NULL, both as a fact:
    ctxt.assert_fact(node, 'ptr', '!=', 0)

    # and as a state:
    ptr = ctxt.find_var(node, 'ptr')
    ctxt.assert_statenames_for_expr(node, ptr, ('ptr.nonnull',))

    # After control flow merges, ptr could be in any state:
    node = ctxt.find_call_of('marker_B')
    ctxt.assert_statenames_for_expr(node, ptr,
                                    ('ptr.start', 'ptr.nonnull'))

    node = ctxt.find_call_of('marker_C')
    # Although we know flag != 0 at marker_C...
    ctxt.assert_fact(node, 'flag', '!=', 0)

    # ...the solver isn't yet smart enough to know that the ptr must be
    # nonnull:
    ctxt.assert_statenames_for_expr(node, ptr,
                                    ('ptr.start', 'ptr.nonnull'))

    node = ctxt.find_call_of('marker_D')
    # Hence the solver erroneously has multiple states for ptr at marker_D:
    ctxt.assert_statenames_for_expr(node, ptr,
                                    ('ptr.start', 'ptr.nonnull', 'ptr.free'))
    # (where "ptr.nonnull" isn't actually possible: it will have been freed)

    # Verify that checker is looking for a possible leak of ptr:
    node = ctxt.find_exit_of('test')
    leakedge = ctxt.get_inedge(node)
    pm = ctxt.assert_edge_matches_pattern(leakedge, '$leaked$')
    assert str(pm.expr) == 'ptr'
    assert pm.statenames == frozenset(['ptr.unchecked', 'ptr.nonnull'])

    # Verify that the solvers find a possible leak due to the (erroneous)
    # ptr.nonnull falling out of scope at the end of the function:
    assert len(ctxt._errors) == 1
    err = ctxt._errors[0]
    assert err.msg == 'leak of ptr'

    # Verify that the error is discovered to be impossible
    # (since flag must be both true *and* false for it to occur):
    ctxt.assert_error_is_impossible(err, solution)
    # (it's thus discarded)

checker = parse_file('sm/checkers/malloc_checker.sm')
main([checker], selftest=selftest)
