# -*- coding: utf-8 -*-
#   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011 Red Hat, Inc.
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

import gcc
from libcpychecker import main, get_traces

def verify_traces(optpass, fun):
    # Only run in one pass
    # FIXME: should we be adding our own pass for this?
    if optpass.name == '*warn_function_return':
        if fun:
            traces = get_traces(fun)

            # We should have one trace
            # print('traces: %r' % traces)
            assert len(traces) == 1

            # Verify the trace:
            state = traces[0].states[-1]
            print('Trace 0:')
            print('  returned: %s' % state.return_rvalue)

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      verify_traces)

from libcpychecker import main
main(verify_refcounting=True,
     show_traces=False)
