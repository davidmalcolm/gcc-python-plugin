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
    PyObject *list;
    PyObject *item;
    list = PyList_New(1);
    if (!list) {
        return NULL;
    }

    item = PyLong_FromLong(42);
    if (!item) {
        Py_DECREF(list);
        return NULL;
    }
    
    /*
      Set the item in the list via the PyList_SET_ITEM macro.

      The checker ought to figure out that the macro has stolen the reference
      to "item", and that this function is thus _not_ leaking a reference to
      "item".
    */
    PyList_SET_ITEM(list, 0, item);

    return list;
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
