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
  Test of handling of Objects/abstract.c's null_error()
*/

PyObject *
test(PyObject *mapping)
{
    PyObject *key;
    PyObject *value;

    /* This could fail (e.g. MemoryError): */
    key = PyString_FromString("some_key");

    /* PyObject_GetItem uses null_error() on both arguments, and thus ought
       to gracefully handle the above call failing, without overriding the
       original exception: */
    value = PyObject_GetItem(mapping, key);
    Py_XDECREF(key);
    return value;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
