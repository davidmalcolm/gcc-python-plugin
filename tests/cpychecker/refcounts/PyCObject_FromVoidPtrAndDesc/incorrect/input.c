/*
   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012 Red Hat, Inc.

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
  Test that we detect a call to PyCObject_FromVoidPtrAndDesc that doesn't
  handle e.g. deprecation failure
*/

struct foo
{
    int i;
    int j;
};

struct foo some_foo;

PyObject *
test(PyObject *self, PyObject *args)
{
    PyObject *obj = PyCObject_FromVoidPtrAndDesc(&some_foo, "struct foo", NULL);

    /*
      This is incorrect: there's no error handling for if the call above
      fails, and there's a reference leak on "obj" even if it succeeds:
    */
    return PyTuple_Pack(2, self, obj);
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
