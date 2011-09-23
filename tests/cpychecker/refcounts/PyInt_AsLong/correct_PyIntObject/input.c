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
  Test that PyInt_AsLong works for the case where we know it's a PyIntObject
*/

extern void __cpychecker_dump(long val);

PyObject *
test(PyObject *self, PyObject *args)
{
    PyObject *int_obj;
    long long_val;

    /* This call can't fail, since we're in the interval [-5..257) */
    int_obj = PyInt_FromLong(42);

    /* Verify that we can roundtrip the underlying int: */
    long_val = PyInt_AsLong(int_obj);
    __cpychecker_dump(long_val);

    return int_obj;
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
