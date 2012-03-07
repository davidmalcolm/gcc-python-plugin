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

/* Verify that the checker will run on C++ code */

PyObject *
test(int i)
{
    if (i) {
        /* 
           Verify that C++ frontend can locate globals
           for types ("PyDict_Type") and exceptions (PyExc_MemoryError)
        */
        return PyDict_New();
    } else {
        /* Verify that bugs are reported: 
           this code is missing a Py_INCREF on Py_None */
        return Py_None;
    }
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
