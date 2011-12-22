/*
   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011 Red Hat, Inc.

   This is free software: you can redistribute it and/or modify it
   under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see
   <http://www.gnu.org/licenses/>.
*/

#include <Python.h>

/*
  Test of detection of bogus types/lack of NULL termination in a call to
  PyObject_CallMethodObjArgs
*/

struct FooObject {
    PyObject_HEAD
    int i;
};

PyObject *
test(PyObject *obj, PyObject *a, struct FooObject *b)
{
    PyObject *name = PyString_FromString("some_method");
    PyObject *result;
    if (!name) {
        return NULL;
    }
    /* BUG: these types are completely wrong:
       the function expects a NULL-terminated sequence of (PyObject*)
    */
    result = PyObject_CallMethodObjArgs(obj, name,
                                        "(s, s, s, s)",
                                        "fee", "fi", "fo", "fum");
    Py_DECREF(name);
    return result;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
