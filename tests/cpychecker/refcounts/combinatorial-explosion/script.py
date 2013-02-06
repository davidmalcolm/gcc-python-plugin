# -*- coding: utf-8 -*-
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

import atexit
import os
import sys

from firehose.report import Analysis, Failure

from libcpychecker import main, Options

XML_OUTPUT_PATH = 'tests/cpychecker/refcounts/combinatorial-explosion/output.xml'

def assertEqual(lhs, rhs):
    if lhs != rhs:
        raise ValueError('non-equal values: %r != %r' % (lhs, rhs))

def verify_analysis(analysis):
    # Verify that a Failure instance made it into the firehose output:
    assertEqual(len(analysis.results), 1)
    f = analysis.results[0]

    assert isinstance(f, Failure)

    assertEqual(f.location.file.givenpath,
                'tests/cpychecker/refcounts/combinatorial-explosion/input.c')
    assertEqual(f.location.function.name, 'test_adding_module_objects')
    assertEqual(f.stdout, None)
    assertEqual(f.stderr,
                ('this function is too complicated for the reference-count'
                 ' checker to fully analyze: not all paths were analyzed'))
    assertEqual(f.returncode, None)

def verify_firehose():
    global ctxt
    sys.stderr.write('verify_firehose()\n')
    assert ctxt.was_flushed

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
                    dump_traces=False,
                    show_traces=False,
                    outputxmlpath=XML_OUTPUT_PATH))
if 0:
    sys.stderr.write('%s\n' % atexit._exithandlers)
