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
handle_SetItem(PyObject *self, PyObject *args)
{
    PyObject *tuple;
    PyObject *item;
    tuple = PyTuple_New(1);
    if (!tuple) {
        return NULL;
    }

    item = PyLong_FromLong(42);
    if (!item) {
        Py_DECREF(tuple);
        return NULL;
    }
    
    /*
      Set the item in the tuple via PyTuple_SetItem()

      The checker ought to figure out that the macro has stolen the reference
      to "item", and that this function is thus _not_ leaking a reference to
      "item".
    */
    PyTuple_SetItem(tuple, 0, item);

    return tuple;
}
static PyMethodDef test_methods[] = {
    {"test_method",  handle_SetItem, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
