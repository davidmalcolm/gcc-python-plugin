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

/* Examples of mistakes made using the Python API */
#include <Python.h>

extern uint16_t htons(uint16_t hostshort);

#if PY_MAJOR_VERSION >= 3
#define PYINT_FROMLONG(l) (PyLong_FromLong(l))
#else
#define PYINT_FROMLONG(l) (PyInt_FromLong(l))
#endif

PyObject *
socket_htons(PyObject *self, PyObject *args)
{
    unsigned long x1, x2;

    if (!PyArg_ParseTuple(args, "i:htons", &x1)) {
        return NULL;
    }
    x2 = (int)htons((short)x1);
    return PYINT_FROMLONG(x2);
}

PyObject *
not_enough_varargs(PyObject *self, PyObject *args)
{
   if (!PyArg_ParseTuple(args, "i")) {
       return NULL;
   }
   Py_RETURN_NONE;
}

PyObject *
too_many_varargs(PyObject *self, PyObject *args)
{
    int i, j;
    if (!PyArg_ParseTuple(args, "i", &i, &j)) {
	 return NULL;
    }
    Py_RETURN_NONE;
}

PyObject *
kwargs_example(PyObject *self, PyObject *args, PyObject *kwargs)
{
    double x, y;
    char *keywords[] = {"x", "y"};

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "(ff):kwargs_example", keywords, &x, &y)) {
	 return NULL;
    }
    Py_RETURN_NONE;
}


extern int convert_to_ssize(PyObject *, Py_ssize_t *);

PyObject *
buggy_converter(PyObject *self, PyObject *args)
{
    int i;

    if (!PyArg_ParseTuple(args, "O&", convert_to_ssize, &i)) {
        return NULL;
    }

    Py_RETURN_NONE;
}

PyObject *
make_a_list_of_random_ints_badly(PyObject *self,
                                 PyObject *args)
{
    PyObject *list, *item;
    long count, i;

    if (!PyArg_ParseTuple(args, "i", &count)) {
         return NULL;
    }

    list = PyList_New(0);

    for (i = 0; i < count; i++) {
        item = PyLong_FromLong(random());
        PyList_Append(list, item);
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
