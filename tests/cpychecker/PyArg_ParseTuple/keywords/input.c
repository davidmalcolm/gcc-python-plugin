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
  A simple check of PyArg_ParseTupleAndKeywords
*/

#include <Python.h>

static PyObject *
parse_to_a_typedef(PyObject *self, PyObject *args, PyObject *kwargs)
{
    int val;
    static char *keywords[] = { "hi" }; /* Note no NULL terminator.  */

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "i", keywords, &val)) {
        return NULL;
    }

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "i", NULL, &val)) {
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
