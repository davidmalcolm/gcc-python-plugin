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

extern void not_returning_int(void);
extern int not_enough_args(PyObject *);
extern int too_many_args(PyObject *, int *, int);
extern int not_taking_PyObjectPtr(int, int);
extern int convert_to_ssize(PyObject *, Py_ssize_t *);

PyObject *
incorrect_usages_of_converter(PyObject *self, PyObject *args)
{
    int i0;
    int i1;
    Py_ssize_t ssize0;

    /* Not enough args: */
    if (!PyArg_ParseTuple(args, "O&")) {
        return NULL;
    }
    if (!PyArg_ParseTuple(args, "O&", 42)) {
        return NULL;
    }

    /* First arg not even a pointer: */
    if (!PyArg_ParseTuple(args, "O&", 42, &i1)) {
        return NULL;
    }

    /* First arg not a function: */
    if (!PyArg_ParseTuple(args, "O&", &i0, &i1)) {
        return NULL;
    }

    /* Signature of callback is wrong: */
    if (!PyArg_ParseTuple(args, "O&", not_returning_int, &i1)) {
        return NULL;
    }
    if (!PyArg_ParseTuple(args, "O&", not_enough_args, &i1)) {
        return NULL;
    }
    if (!PyArg_ParseTuple(args, "O&", too_many_args, &i1)) {
        return NULL;
    }
    if (!PyArg_ParseTuple(args, "O&", not_taking_PyObjectPtr, &i1)) {
        return NULL;
    }

    /* Second arg is not a pointer */
    if (!PyArg_ParseTuple(args, "O&", convert_to_ssize, 42)) {
        return NULL;
    }

    /* Mismatching second arg: */
    if (!PyArg_ParseTuple(args, "O&", convert_to_ssize, &i0)) {
        return NULL;
    }

    /* Correct usage: */
    if (!PyArg_ParseTuple(args, "O&", convert_to_ssize, &ssize0)) {
        return NULL;
    }

    Py_RETURN_NONE;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
