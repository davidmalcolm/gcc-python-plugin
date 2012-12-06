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

from sm import main
from sm.parser import parse_file
from sm.solver import State

def selftest(ctxt, solution):
    if 0:
        import sys
        solution.dump(sys.stderr)

    # Verify that ptr doesn't change state due to
    #     ptr = malloc(i);
    # since the checker only tracks constant integer values:
    node = ctxt.find_call_of('malloc')
    ctxt.assert_statenames_for_varname(node, 'ptr', {'ptr.all'})

    node = ctxt.get_successor(node)
    ctxt.assert_statenames_for_varname(node, 'ptr', {'ptr.all'})

checker = parse_file('sm/checkers/sizeof_allocation.sm')
main([checker], selftest=selftest)
