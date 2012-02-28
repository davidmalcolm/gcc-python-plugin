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
  Ensure that the checker can cope with calls to a function that it doesn't
  recognize that returns a PyObject subclass:
*/
typedef struct FooObject {
    PyObject_HEAD
    int i;
} FooObject;

extern FooObject *make_foo(int i);

PyObject *
test(PyObject *self, PyObject *args)
{
    FooObject *f = make_foo(42);
    if (NULL == f) {
        return NULL; /* we assume an exception was set by make_foo() */
    }
    Py_DECREF(f);

    Py_RETURN_NONE;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
