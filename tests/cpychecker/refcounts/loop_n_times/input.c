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
  Verify that the checker can cope with a loop where we can't know
  the limit at analysis time
*/

PyObject *
loop_n_times(PyObject *self, PyObject *args)
{
    int i, count;
    PyObject *list;
    PyObject *item;

    if (!PyArg_ParseTuple(args, "i", &count)) {
        return NULL;
    }

    list = PyList_New(count);
    if (!list) {
        return NULL;
    }
    item = PyLong_FromLong(42);
    if (!item) {
        Py_DECREF(list);
        return NULL;
    }

    /* We can't know the value of "count" at this point: */
    for (i = 0; i < count; i++) {
        /* This steals a reference to item, so we need to INCREF it: */
        Py_INCREF(item);
        PyList_SetItem(list, 0, item);
    }
    Py_DECREF(item);
    return list;
}
static PyMethodDef test_methods[] = {
    {"test_method",  loop_n_times, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
