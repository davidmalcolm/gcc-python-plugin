#   Copyright 2011, 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011, 2013 Red Hat, Inc.
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

from libcpychecker import main

def assertEqual(lhs, rhs):
    if lhs != rhs:
        raise ValueError('non-equal values: %r != %r' % (lhs, rhs))

def selftest(ctxt, fun):
    assertEqual(len(ctxt.analysis.results), 2)

    issue0 = ctxt.analysis.results[0]
    assertEqual(issue0.testid, 'mismatching-type-in-format-string')

    # Verify that the issue contains meaningful custom fields:
    assertEqual(issue0.customfields['function'], 'PyArg_ParseTuple')
    assertEqual(issue0.customfields['format-code'], 'S')
    assertEqual(issue0.customfields['full-format-string'], 'SU')
    assertEqual(issue0.customfields['expected-type'],
                'one of "struct PyStringObject * *" or "struct PyObject * *"')
    assertEqual(issue0.customfields['actual-type'], '"int *" (pointing to 32 bits)')
    assertEqual(issue0.customfields['expression'], '&val1')
    assertEqual(issue0.customfields['argument-num'], 3)

main(selftest=selftest)
