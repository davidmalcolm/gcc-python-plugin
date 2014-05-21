/*
   Copyright 2014 David Malcolm <dmalcolm@redhat.com>
   Copyright 2014 Red Hat, Inc.

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
  Test that we report a sane return location when returning prematurely
  from a function, at the source location of the "return"
*/

PyObject *
test(PyObject *self, PyObject *args)
{
    PyObject *dictA;
    PyObject *dictB;
    dictA = PyDict_New();
    if (!dictA) return NULL;

    /* dictA now has a refcnt of 1 */

    dictB = PyDict_New();
    if (!dictB) return NULL;

    /* the above error-handling code leaks the ref on dictA */

    Py_DECREF(dictA);

    return dictB;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
