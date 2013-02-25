/*
   Copyright 2013 David Malcolm <dmalcolm@redhat.com>
   Copyright 2013 Red Hat, Inc.

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
test(PyObject *obj)
{
    PyObject *list = NULL;
    PyObject *item = NULL;
    
    list = PyList_New(3);
    if (!list) {
        goto error;
    }

    item = PyInt_FromLong(42);
    if (!item) {
        goto error;
    }

    Py_INCREF(item);
    PyList_SetItem(list, 0, item);
    Py_INCREF(item);
    PyList_SetItem(list, 1, item);
    Py_INCREF(item);
    PyList_SetItem(list, 2, item);

    Py_DECREF(item);

    return list;

 error:
    Py_XDECREF(item);
    Py_XDECREF(list);
    return NULL;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
