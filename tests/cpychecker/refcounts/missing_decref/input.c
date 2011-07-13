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

PyObject *
missing_decref(PyObject *self, PyObject *args)
{
    PyObject *list;
    PyObject *item;
    list = PyList_New(1);
    if (!list)
        return NULL;
    item = PyLong_FromLong(42);
    /* This error handling is incorrect: it's missing an
       invocation of Py_DECREF(list): */
    if (!item)
        return NULL;
    /* This steals a reference to item; item is not leaked when we get here: */
    PyList_SetItem(list, 0, item);
    return list;
}
static PyMethodDef test_methods[] = {
    {"test_method",  missing_decref, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL} /* Sentinel */
};
