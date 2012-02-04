/*
   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012 Red Hat, Inc.

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
  Verify that the checker warns about function calls that are passed
  deallocated objects:
*/
extern void foo(PyObject *);

void
passing_dead_object_to_function(PyObject *self, PyObject *args)
{
    /* Create an object: */
    PyObject *tmp = PyLong_FromLong(0x1000);

    if (!tmp) {
        return;
    }

    /*
      Now decref the object.  Depending on what other references are owned
      on the object, it can reach a refcount of zero, and thus be deallocated.
    */
    Py_DECREF(tmp);

    /* This is an error: the object being returned may have been deallocated */
    foo(tmp);
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
