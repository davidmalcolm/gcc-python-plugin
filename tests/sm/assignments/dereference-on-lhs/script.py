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

    # Verify that the:
    #    foo = malloc()
    # transitions "foo" from "ptr.all" to "ptr.unknown"
    node = ctxt.find_call_of('malloc')
    ctxt.assert_statenames_for_varname(node, 'foo', {'ptr.all'})

    node = ctxt.get_successor(node)
    ctxt.assert_statenames_for_varname(node, 'foo', {'ptr.unknown'})

    verify_json(ctxt, solution)

def verify_json(ctxt, solution):
    # Verify that the JSON version of the report is sane:
    assert len(ctxt._errors) == 1
    err = ctxt._errors[0]
    report = err.make_report(ctxt, solution)

    json = report.as_json()

    if 0:
        import json as jsonmod
        print(jsonmod.dumps(report.as_json(),
                            sort_keys=True,
                            indent=4, separators=(',', ': ')))

    # Verify json['sm']:
    assert json['sm']['name'] == 'malloc_checker'

    # Verify json['loc']:
    assert 'input.c' in json['loc']['actualfilename']
    assert json['loc']['givenfilename'] == "tests/sm/assignments/dereference-on-lhs/input.c"
    assert json['loc']['line'] == 25
    assert json['loc']['column'] == 8

    # Verify json['message']:
    assert json['message'] == "use of possibly-NULL pointer foo"

    # Verify json['notes']:
    assert len(json['notes']) == 2
    note = json['notes'][0]
    assert json['loc']['givenfilename'] == "tests/sm/assignments/dereference-on-lhs/input.c"
    assert note['loc']['line'] == 24
    assert note['message'] == "foo assigned to the result of malloc()"

checker = parse_file('sm/checkers/malloc_checker.sm')
main([checker], selftest=selftest)
