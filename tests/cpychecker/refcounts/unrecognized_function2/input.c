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
  Ensure that the checker can cope with calls to a function that it doesn't
  recognize:
*/
extern PyObject *foo(int i);

PyObject *
call_to_unrecognized_function(PyObject *self, PyObject *args)
{
    PyObject *tmp;

    /* Call an unrecognized function: */
    tmp = foo(42);
    if (!tmp) {
        return NULL;
    }

    /* Verify that tp_dealloc is sane: */
    Py_DECREF(tmp);

    /* Now do it again, to get a sane return value: */
    return foo(42);
}
static PyMethodDef test_methods[] = {
    {"test_method",  call_to_unrecognized_function, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
