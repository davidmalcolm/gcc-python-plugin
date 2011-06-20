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

PyObject*
my_method_A(PyObject *self, PyObject *args)
{
    Py_RETURN_NONE;
}

PyObject*
my_method_B(PyObject *self, PyObject *args)
{
    Py_RETURN_NONE;
}

static PyMethodDef def_table[] = {
    {"my_method_A",  my_method_A, METH_VARARGS, NULL},
    {"my_method_B",  my_method_B, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL} /* Sentinel */
};


