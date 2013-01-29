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

# Verify that the JSON serialization of error reports is working

import os

from firehose.report import Analysis

import gcc

from libcpychecker import Context, Options
from libcpychecker.refcounts import impl_check_refcounts

XML_OUTPUT_PATH = 'tests/cpychecker/refcounts/xml/basic/output.xml'

def assertEqual(lhs, rhs):
    if lhs != rhs:
        raise ValueError('non-equal values: %r != %r' % (lhs, rhs))

def verify_analysis(analysis):
    assertEqual(len(analysis.results), 1)
    w = analysis.results[0]

    assertEqual(w.cwe, None)
    assertEqual(w.testid, 'refcount-too-low')
    assertEqual(w.location.file.givenpath,
                'tests/cpychecker/refcounts/xml/basic/input.c')
    assertEqual(w.location.function.name, 'losing_refcnt_of_none')
    assertEqual(w.location.line, 26)
    assertEqual(w.location.column, 5)
    assertEqual(w.message.text, 'ob_refcnt of return value is 1 too low')
    assertEqual(w.notes, None) # FIXME
    # FIXME: we ought to get this:
    #   "was expecting final ob_refcnt to be N + 1 (for some unknown N)")
    #   "due to object being referenced by: return value")
    #   "but final ob_refcnt is N + 0")
    #   "consider using \"Py_RETURN_NONE;\"")

    # Verify what we captured for the endstate within the report:
    endstate = w.trace.states[-1]

    # Verify that we have a location:
    assertEqual(endstate.location.line, 26)
    assert endstate.location.column > 0

    assertEqual(endstate.notes, None)

    '''
    vars = statejs['variables']

    # Verify that the bug in the handling of Py_None's ob_refcnt
    # is described within the JSON:
    none_refcnt = vars['_Py_NoneStruct.ob_refcnt']
    assertEqual(none_refcnt['gcctype'], "Py_ssize_t")
    assertEqual(none_refcnt['kind'], "RefcountValue")
    assertEqual(none_refcnt['actual_ob_refcnt']['refs_we_own'], 0)
    assertEqual(none_refcnt['expected_ob_refcnt']['pointers_to_this'],
                ['return value'])

    # Verify "self":
    selfjs = vars['self']
    assertEqual(selfjs['gcctype'], 'struct PyObject *')
    assertEqual(selfjs['kind'], 'PointerToRegion')
    assertEqual(selfjs['value_comes_from'][0]['line'], 23)

    ob_refcnt = vars['self->ob_refcnt']
    assertEqual(ob_refcnt['gcctype'], 'Py_ssize_t')
    assertEqual(ob_refcnt['kind'], 'RefcountValue')
    assertEqual(ob_refcnt['value_comes_from'][0]['line'], 23)

    ob_type = vars['self->ob_type']
    assertEqual(ob_type['gcctype'], 'struct PyTypeObject *')
    assertEqual(ob_type['kind'], 'PointerToRegion')
    assertEqual(ob_type['value_comes_from'][0]['line'], 23)
    '''

def verify_firehose(optpass, fun):
    # Only run in one pass
    # FIXME: should we be adding our own pass for this?
    if optpass.name == '*warn_function_return':
        if fun:
            ctxt = Context(outputxmlpath=XML_OUTPUT_PATH)
            rep = impl_check_refcounts(ctxt, fun, Options())
            rep.flush()
            ctxt.flush()

            if 0:
                print(ctxt.analysis.to_xml_str())

            assertEqual(len(ctxt.analysis.results), 1)
            w = ctxt.analysis.results[0]

            verify_analysis(ctxt.analysis)

            # Verify that the XML was written:
            with open(XML_OUTPUT_PATH) as f:
                analysis_from_disk = Analysis.from_xml(f)
            # Verify that everything made it to disk:
            verify_analysis(analysis_from_disk)

            os.unlink(XML_OUTPUT_PATH)

            # Ensure that this testing code actually got run (stdout is
            # checked):
            print('GOT HERE')

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      verify_firehose)
