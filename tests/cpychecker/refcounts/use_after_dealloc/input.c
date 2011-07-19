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
  Verify that the checker warns about attempts to use an object
  after it might have been deallocated
*/
PyObject *
use_after_dealloc(PyObject *self, PyObject *args)
{
    /* Create an object: */
    PyObject *tmp = PyLong_FromLong(0x1000);

    if (!tmp) {
        return NULL;
    }

    /*
      Now decref then incref the object.  The object reaches a refcount
      of zero, and thus is deallocated; and the subsequent INCREF is
      accessing that deallocated memory:
    */
    Py_DECREF(tmp);
    Py_INCREF(tmp);

    /* This is an error: the object being returned has been deallocated */
    return tmp;
}
static PyMethodDef test_methods[] = {
    {"test_method",  use_after_dealloc, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
