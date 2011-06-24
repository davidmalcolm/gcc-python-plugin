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

/*
  Verify that the checker can cope with format codes that reference
  specific object subtypes (e.g. PyStringObject) but are supplied
  a PyObject ** instead.

  This was erroneously giving errors like this:
    error: Mismatching type in call to PyArg_ParseTuple with format code "S" [-fpermissive]
      argument 3 ("&stringobj") had type "struct PyObject * *"
      but was expecting "PyStringObject * *" for format code "S"
  which is overconstraining things: a (PyObject**) is fine there.
*/

#include <Python.h>

static PyObject *
less_rigid_code_S(PyObject *self, PyObject *args)
{
    /*
       Both of these ought to be acceptable for code "S":
    */
    PyObject *S_baseobj;
    PyStringObject *S_stringobj;

    if (!PyArg_ParseTuple(args, "SS",
			  &S_baseobj,
                          &S_stringobj)) {
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject *
less_rigid_code_U(PyObject *self, PyObject *args)
{
    /*
       Both of these ought to be acceptable for code "U":
    */
    PyObject *U_baseobj;
    PyUnicodeObject *U_uniobj;

    if (!PyArg_ParseTuple(args, "UU",
			  &U_baseobj,
                          &U_uniobj)) {
        return NULL;
    }

    Py_RETURN_NONE;
}
