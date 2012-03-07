/*
   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012 Red Hat, Inc.

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
  Test that PyFloat_AsDouble works for the case where we don't know if it's
  a PyFloatObject
*/

extern void __cpychecker_dump(double val);

PyObject *
test(PyObject *self, PyObject *args)
{
    double double_val;

    double_val = PyFloat_AsDouble(self);
    if (-1 == double_val) {
        if (PyErr_Occurred()) {
            /* Unsuccessful coercion to "double": */
            return NULL;
        } else {
            /* Successful coercion to "double";
               it just happened to be -1: */
            __cpychecker_dump(double_val);
        }
    } else {
        /* Successful coercion to "double": */
        __cpychecker_dump(double_val);
    }

    Py_RETURN_NONE;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
