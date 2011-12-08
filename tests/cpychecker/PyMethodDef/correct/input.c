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
  http://docs.python.org/c-api/structures.html#PyMethodDef
*/

/*
  Verify that the analyser can cope with various function signatures within
  a table of PyMethodDef initializers
*/

typedef struct MySubclass {
    PyObject_HEAD
    struct foo *f;
} MySubclass;

static PyObject *
correct_pycfunction(PyObject *self, PyObject *args)
{
    Py_RETURN_NONE;
}

static PyObject *
correct_subclass(MySubclass *self, PyObject *args)
{
    Py_RETURN_NONE;
}

static PyObject *
correct_pycfunction_with_keywords(PyObject *self, PyObject *args, PyObject *kwargs)
{
    Py_RETURN_NONE;
}

/* etc */

static PyMethodDef methods[] = {
    {"test1", 
     (PyCFunction)correct_pycfunction,
     0, /* ml_flags */
     NULL},

    {"test2", 
     (PyCFunction)correct_subclass,
     0, /* ml_flags */
     NULL},

    {"test3", 
     (PyCFunction)correct_pycfunction_with_keywords,
     (METH_VARARGS | METH_KEYWORDS),
     NULL},

    {NULL, NULL, 0, NULL} /* Sentinel */
};

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
