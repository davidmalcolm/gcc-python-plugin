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

# Selftest of Options(reportstats=True)

import sys

from firehose.model import Analysis, Failure

from libcpychecker import main, Options
from libcpychecker.refcounts import CPython

def assertEqual(lhs, rhs):
    if lhs != rhs:
        raise ValueError('non-equal values: %r != %r' % (lhs, rhs))

def selftest(ctxt, fun):
    # Verify that info about the function made it into the report
    assertEqual(len(ctxt.analysis.results), 1)
    info0 = ctxt.analysis.results[0]
    assertEqual(info0.infoid, 'stats')
    assertEqual(info0.location.function.name, 'test')
    assertEqual(info0.customfields['num_Py_api_calls'], 5)
    assertEqual(info0.customfields['calls_to_PyList_New'], 1)
    assertEqual(info0.customfields['calls_to_PyInt_FromLong'], 1)
    assertEqual(info0.customfields['calls_to_PyList_SetItem'], 3)

    assert info0.customfields['num_basic_blocks'] > 10
    assert info0.customfields['num_edges'] > 10
    assert info0.customfields['num_gimple_statements'] > 10

main(Options(verify_refcounting=True,
             reportstats=True,
             selftest=selftest))
