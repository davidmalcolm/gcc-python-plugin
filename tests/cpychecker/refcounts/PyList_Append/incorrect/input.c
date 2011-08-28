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
  Test of incorrect reference-handling in a call to PyList_Append
*/

PyObject *
test(PyObject *self, PyObject *args)
{
    PyObject *list;
    PyObject *item;

    list = PyList_New(0);
    if (!list) {
        return NULL;
    }
    item = PyLong_FromLong(42);
    if (!item) {
        Py_DECREF(list);
        return NULL;
    }

    if (-1 == PyList_Append(list, item)) {
        Py_DECREF(list);
        Py_DECREF(item);
        return NULL;
    }

    /* 
       PyList_Append adds a ref to the item, but we still own a reference to
       it, so this path through the function leaks the reference.
     */

    return list;
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
