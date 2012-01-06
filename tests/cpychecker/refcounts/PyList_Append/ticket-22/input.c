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
  https://fedorahosted.org/gcc-python-plugin/ticket/22
  Test of:
     PyList_Append(list, item)
  where item is an UnknownValue
*/

extern PyObject *ptr;

PyObject *
test(PyObject *self)
{
    PyObject *list;
    PyObject *item;

    list = PyList_New(0);
    if (!list) {
        return NULL;
    }

    if (-1 == PyList_Append(list, ptr)) {
        Py_DECREF(list);
        return NULL;
    }

    return list;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
