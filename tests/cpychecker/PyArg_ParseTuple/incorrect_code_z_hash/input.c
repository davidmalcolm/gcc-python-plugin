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
  Verify that the error message for bad types for code "z#" is correct
  Bug reported in:
    https://fedorahosted.org/pipermail/gcc-python-plugin/2011-June/000007.html
*/

#include <Python.h>

static PyObject *
incorrect_code_z_hash(PyObject *self, PyObject *args)
{
    const char *str;
    float len; /* This is incorrect; should be "int" */

    if (!PyArg_ParseTuple(args, "z#", &str, &len)) {
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
