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

###########################################################################
# Selftest of JSON report dumping
#
# This is the same code and checker as:
#    tests/sm/assignments/dereference-on-lhs
# but with the output sent to JSON
###########################################################################

import glob
import json

from sm import main
from sm.options import Options
from sm.parser import parse_file

def get_json_reports():
    return glob.glob('tests/sm/json/input.c.*.sm.json')

def delete_json_reports():
    for jsonfile in get_json_reports():
        os.unlink(jsonfile)

def selftest(ctxt, solution):
    if 0:
        import sys
        solution.dump(sys.stderr)

    # Verify the JSON version of the report directly from the Error object:
    assert len(ctxt._errors) == 1
    err = ctxt._errors[0]
    report = err.make_report(ctxt, solution)

    jsonobj = report.as_json()
    verify_json(jsonobj)
    print('OK: verified in-memory JSON object')

    # Verify that a JSON file was written and check its contents:
    jsonfiles = get_json_reports()
    assert len(jsonfiles) == 1
    with open(jsonfiles[0], 'r') as f:
        jsonobj = json.load(f)
    verify_json(jsonobj)
    print('OK: verified JSON object parsed from disk')

    # On success, keep the directory clean:
    if 1:
        delete_json_reports()

def verify_json(jsonobj):
    if 0:
        print(json.dumps(jsonobj,
                         sort_keys=True,
                         indent=4, separators=(',', ': ')))

    # Verify jsonobj['cwe']:
    assert jsonobj['cwe'] == 'CWE-690'

    # Verify jsonobj['sm']:
    assert jsonobj['sm']['name'] == 'malloc_checker'
    assert jsonobj['sm']['filename'] == 'sm/checkers/malloc_checker.sm'
    assert jsonobj['sm']['line'] == 23

    # Verify jsonobj['loc']:
    assert 'input.c' in jsonobj['loc']['actualfilename']
    assert jsonobj['loc']['givenfilename'] == "tests/sm/json/input.c"
    assert jsonobj['loc']['line'] == 25
    assert jsonobj['loc']['column'] == 8

    # Verify jsonobj['message']:
    assert jsonobj['message'] == "use of possibly-NULL pointer foo"

    # Verify jsonobj['notes']:
    assert len(jsonobj['notes']) == 2
    note = jsonobj['notes'][0]
    assert jsonobj['loc']['givenfilename'] == "tests/sm/json/input.c"
    assert note['loc']['line'] == 24
    assert note['message'] == "foo assigned to the result of malloc()"

# Preprocessing: remove any existing json error reports:
delete_json_reports()

checker = parse_file('sm/checkers/malloc_checker.sm')
main([checker],
     # Dump JSON files rather than writing to stderr:
     options=Options(dump_json=True),
     selftest=selftest, )
