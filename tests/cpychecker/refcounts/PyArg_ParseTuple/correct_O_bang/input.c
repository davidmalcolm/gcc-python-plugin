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
  that uses the "O!" format code, with a type that we don't know about
*/

struct FooObject {
    PyObject_HEAD
    char *msg;
};

extern PyTypeObject foo_type;

PyObject *
test(PyObject *self, PyObject *args)
{
    struct FooObject *foo_obj;

    if (!PyArg_ParseTuple(args, "O!:test",
                          &foo_type, &foo_obj)) {
        return NULL;
    }

    /*
      We now have a borrowed non-NULL ref to the FooObject; the checker
      ought not to complain.

      (It doesn't know that msg is non-NULL or not, but should not issue
      a message about that)
    */

    return PyString_FromString(foo_obj->msg);
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
