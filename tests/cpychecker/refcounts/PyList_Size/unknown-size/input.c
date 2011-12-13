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
  Test of a call to PyList_Size where we don't know the size
*/

Py_ssize_t
test(PyObject *list)
{
    Py_ssize_t tmpA, tmpB;
    tmpA = PyList_Size(list);
    tmpB = PyList_Size(list);
    if (tmpA == tmpB) {
        /* they ought to be provably the same */
        return 42;
    } else {
        /* this should not occur */
        return -1;
    }
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
