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
  Test that PyInt_AsLong works for the case where we don't know if it's
  a PyIntObject
*/

extern void __cpychecker_dump(long val);

PyObject *
test(PyObject *self, PyObject *args)
{
    long long_val;

    long_val = PyInt_AsLong(self);
    if (-1 == long_val) {
        if (PyErr_Occurred()) {
            /* Unsuccessful coercion to "long": */
            return NULL;
        } else {
            /* Successful coercion to "long";
               it just happened to be -1: */
            __cpychecker_dump(long_val);
        }
    } else {
        /* Successful coercion to "long": */
        __cpychecker_dump(long_val);
    }

    Py_RETURN_NONE;
}
static PyMethodDef test_methods[] = {
    {"test_method",  test, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
