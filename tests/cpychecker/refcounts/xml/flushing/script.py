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

# Verify that the final flushing of XML error reports is working

import atexit
import os
import sys

from firehose.model import Analysis

from libcpychecker import main, Options

XML_OUTPUT_PATH = 'tests/cpychecker/refcounts/xml/flushing/output.xml'

def assertEqual(lhs, rhs):
    if lhs != rhs:
        raise ValueError('non-equal values: %r != %r' % (lhs, rhs))

def verify_analysis(analysis):
    assertEqual(len(analysis.results), 1)
    w = analysis.results[0]

    assertEqual(w.cwe, None)
    assertEqual(w.testid, 'refcount-too-low')
    assertEqual(w.location.file.givenpath,
                'tests/cpychecker/refcounts/xml/flushing/input.c')
    assertEqual(w.location.function.name, 'losing_refcnt_of_none')
    assertEqual(w.location.line, 26)
    assertEqual(w.location.column, 5)
    assertEqual(w.message.text, 'ob_refcnt of return value is 1 too low')

def verify_firehose():
    global ctxt
    sys.stderr.write('verify_firehose()\n')
    assert ctxt.was_flushed

    assertEqual(len(ctxt.analysis.results), 1)
    w = ctxt.analysis.results[0]

    verify_analysis(ctxt.analysis)

    # Verify that the XML was actually written:
    with open(XML_OUTPUT_PATH) as f:
        analysis_from_disk = Analysis.from_xml(f)
    # Verify that everything made it to disk:
    verify_analysis(analysis_from_disk)

    os.unlink(XML_OUTPUT_PATH)

    # Ensure that this testing code actually got run (stdout is
    # checked):
    sys.stderr.write('GOT HERE\n')

atexit.register(verify_firehose)
ctxt = main(Options(verify_refcounting=True,
                    outputxmlpath=XML_OUTPUT_PATH))
if 0:
    sys.stderr.write('%s\n' % atexit._exithandlers)
