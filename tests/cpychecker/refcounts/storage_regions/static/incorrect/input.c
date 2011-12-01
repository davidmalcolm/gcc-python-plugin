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
test(PyObject *self, PyObject *args)
{
    /*
      Test of a static local PyObject*
    */
    static PyObject *cache;

    if (!cache) {
        /*
          If the call succeeds, we own a reference, and that corresponds to
          the permanently stored ptr in "cache" (permanent because it's
          "static")
        */
        cache = PyLong_FromLong(0x1000);
        if (!cache) {
            return NULL;
        }
    }

    /* 
       Return a new reference to the cached value which can't be NULL at this
       point.

       However, this code is incorrect: it doesn't Py_INCREF(cache), and thus
       the refcount is too low:
    */
    return cache;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
