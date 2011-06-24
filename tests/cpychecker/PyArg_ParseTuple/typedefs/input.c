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
  Verify that the checker can cope with typedefs of another type
  c.f. error reported here:
    https://fedorahosted.org/pipermail/gcc-python-plugin/2011-June/000006.html
*/

#include <Python.h>

/* as seen in gdb source code: */
typedef unsigned PY_LONG_LONG gdb_py_ulongest;

static PyObject *
parse_to_a_typedef(PyObject *self, PyObject *args)
{
    gdb_py_ulongest val;

    /*
       "K" expects "unsigned PY_LONG_LONG", which "val" is, via a typedef
    */
    if (!PyArg_ParseTuple(args, "K", &val)) {
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
