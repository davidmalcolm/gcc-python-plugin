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
too_many_increfs(PyObject *self, PyObject *args)
{
    PyObject *tmp;
    tmp = PyLong_FromLong(0x1000);

    /* This INCREF is redundant, and introduces a leak (or a read through
       NULL): */
    Py_INCREF(tmp);
    return tmp;
}

static PyMethodDef test_methods[] = {
    {"test_method",  too_many_increfs, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL} /* Sentinel */
};
