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

import gcc
from libcpychecker import main, get_traces, Context, Options

def verify_traces(optpass, fun):
    # Only run in one pass
    # FIXME: should we be adding our own pass for this?
    if optpass.name == '*warn_function_return':
        if fun:
            ctxt = Context(Options())
            traces = get_traces(fun, ctxt)

            # We should have a single trace
            #print('traces: %r' % traces)
            assert len(traces) == 1
            state = traces[0].states[-1]
            print('_Py_NoneStruct.ob_refcnt: %s'
                  % state.get_value_of_field_by_varname('_Py_NoneStruct', 'ob_refcnt'))
            print('state.return_rvalue: %r' % state.return_rvalue)

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      verify_traces)

main(verify_refcounting=True)
