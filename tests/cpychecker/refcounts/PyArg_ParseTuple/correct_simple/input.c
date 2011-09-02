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
  Test of correct reference-handling in a call to PyArg_ParseTuple
  that uses simple format codes that don't affect reference counting
*/

extern void foo(int i, const char *msg, Py_UNICODE *unicode, int size);

PyObject *
test(PyObject *self, PyObject *args)
{
    int i;
    const char *msg;
    Py_UNICODE *unicode;
    int size;

    if (!PyArg_ParseTuple(args, "isu#:test",
                          &i, &msg, &unicode, &size)) {
        return NULL;
    }

    foo(i, msg, unicode, size);

    Py_RETURN_NONE;
}
static PyMethodDef test_methods[] = {
    {"test_method",  test, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
