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
  Test of incorrect usage of PyArg_UnpackTuple, where the argument count
  is incorrect
*/

PyObject *
test(PyObject *self, PyObject *args)
{
    PyObject *a;
    PyObject *b = Py_None;

    /*
      This call has the wrong number of varargs: 2, where 3 is specified
      as the maximum:
    */
    if (!PyArg_UnpackTuple(args, "test", 1, 3, &a, &b)) {
        return NULL;
    }

    return PyTuple_Pack(2, a, b);
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
