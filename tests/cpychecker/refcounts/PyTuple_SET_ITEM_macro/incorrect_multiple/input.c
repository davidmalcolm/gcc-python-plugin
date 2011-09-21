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
handle_SET_ITEM_macro(PyObject *self, PyObject *args)
{
    PyObject *tuple;
    /* 
       The checker must not get confused by this temporary array:
       the borrowed refs that it stores do not persist beyond the
       lifetime of the function:
    */
    PyObject *items[3];

    tuple = PyTuple_New(3);
    if (!tuple) {
        return NULL;
    }

    /* Construct 3 new references: */
    items[0] = PyLong_FromLong(1000);
    if (!items[0]) {
        Py_DECREF(tuple);
        return NULL;
    }
    items[1] = PyLong_FromLong(2000);
    if (!items[1]) {
        Py_DECREF(items[0]);
        Py_DECREF(tuple);
        return NULL;
    }
    items[2] = PyLong_FromLong(3000);
    if (!items[2]) {
        Py_DECREF(items[1]);
        Py_DECREF(items[0]);
        Py_DECREF(tuple);
        return NULL;
    }
    
    /*
      Set each item in the tuple via the PyTuple_SET_ITEM macro.

      These are stolen references, so at this point the reference counts for
      the PyLongObjects are balanced.
    */
    PyTuple_SET_ITEM(tuple, 0, items[0]);
    PyTuple_SET_ITEM(tuple, 1, items[1]);
    PyTuple_SET_ITEM(tuple, 2, items[2]);

    /*
      Now erroneously increment the reference count on one of them:
    */
    Py_INCREF(items[2]);

    /* This is a leak of items[2]: the 3 new references are owned by the tuple
       but the extra incref above is a leak: */
    return tuple;
}
static PyMethodDef test_methods[] = {
    {"test_method",  handle_SET_ITEM_macro, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
