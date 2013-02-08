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

def assertGreater(lhs, rhs):
    if not (lhs > rhs):
        raise ValueError('%r <= %r' % (lhs, rhs))

def verify_analysis(analysis):
    # Verify that a Failure instance made it into the firehose output:
    assertEqual(len(analysis.results), 1)
    f = analysis.results[0]

    assert isinstance(f, Failure)

    assertEqual(f.failureid, 'too-complicated')
    assertEqual(f.location.file.givenpath,
                'tests/cpychecker/refcounts/combinatorial-explosion/input.c')
    assertEqual(f.location.function.name, 'test_adding_module_objects')
    assertEqual(f.location.line, 31)
    assertEqual(f.location.column, 1)
    assertEqual(f.message.text,
                ('this function is too complicated for the reference-count'
                 ' checker to fully analyze: not all paths were analyzed'))
    assert isinstance(f.customfields['maxtrans'], int)
    assertEqual(f.customfields['maxtrans'], options.maxtrans)
    assertGreater(f.customfields['num_basic_blocks'], 50)
    # 72 with gcc 4.7.2 and python 2.7.3

    assertGreater(f.customfields['num_gimple_statements'], 100)
    # 166 with gcc 4.7.2 and python 2.7.3

    assertEqual(f.customfields['num_Py_api_calls'], 33)
    # 33 with gcc 4.7.2 and python 2.7.3
    # (1 call to PyLong_FromLong, 32 calls to PyModule_AddObject):
    assertEqual(f.customfields['calls_to_PyLong_FromLong'], 1)
    assertEqual(f.customfields['calls_to_PyModule_AddObject'], 32)

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

options = Options(verify_refcounting=True,
                  dump_traces=False,
                  show_traces=False,
                  outputxmlpath=XML_OUTPUT_PATH)
atexit.register(verify_firehose)
ctxt = main(options)
if 0:
    sys.stderr.write('%s\n' % atexit._exithandlers)
