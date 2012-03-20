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

# Verify that the JSON serialization of error reports is working

import gcc
from libcpychecker.refcounts import impl_check_refcounts

def assertEqual(lhs, rhs):
    if lhs != rhs:
        raise ValueError('non-equal values: %r != %r' % (lhs, rhs))

def verify_json(optpass, fun):
    # Only run in one pass
    # FIXME: should we be adding our own pass for this?
    if optpass.name == '*warn_function_return':
        if fun:
            rep = impl_check_refcounts(fun)
            js = rep.to_json(fun)
            if 0:
                from json import dumps
                print(dumps(js, sort_keys=True, indent=4))

            # Verify the top-level JSON that's emitted:
            assertEqual(js['filename'], 'tests/cpychecker/refcounts/json/basic/input.c')
            assertEqual(js['function']['name'], 'losing_refcnt_of_none')
            assertEqual(js['function']['lines'][0], 22)
            assertEqual(js['function']['lines'][1], 28)

            # Verify the JSON for the single error report:
            assertEqual(len(js['reports']), 1)
            r = js['reports'][0]
            assertEqual(r['severity'], "warning")
            assertEqual(r['message'], "ob_refcnt of return value is 1 too low")
            assertEqual(len(r['notes']), 4)
            assertEqual(r['notes'][0]['message'],
                        "was expecting final ob_refcnt to be N + 1 (for some unknown N)")
            assertEqual(r['notes'][1]['message'],
                        "due to object being referenced by: return value")
            assertEqual(r['notes'][2]['message'],
                        "but final ob_refcnt is N + 0")
            assertEqual(r['notes'][3]['message'],
                        "consider using \"Py_RETURN_NONE;\"")

            # Verify the JSON serialization of the endstate within the report:
            statejs = r['states'][-1]

            if 0:
                from json import dumps
                print(dumps(statejs, sort_keys=True, indent=4))

            # Verify that we have a location:
            for i in range(2):
                assert statejs['location'][i]['column'] > 0
                assertEqual(statejs['location'][i]['line'], 26)

            assertEqual(statejs['message'], None)

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

            # Ensure that this testing code actually got run (stdout is
            # checked):
            print('GOT HERE')

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      verify_json)
