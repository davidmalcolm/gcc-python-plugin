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
  Test of correct reference-handling when dealing with a callback that
  constructs an object
*/

PyObject *
test(PyObject *(*ctor)(void))
{
    PyObject *dict = NULL;
    PyObject *key = NULL;
    PyObject *value = NULL;

    dict = PyDict_New();
    if (!dict) {
	goto error;
    }

    key = PyLong_FromLong(500);
    if (!key) {
        goto error;
    }

    /*
      Invoke the callback; the checker will assume that it follows normal
      object ownership rules:
    */
    value = (*ctor)();
    if (!value) {
        /* should have set an exception */
        goto error;
    }

    if (-1 == PyDict_SetItem(dict, key, value)) {
        goto error;
    }
    /*
       The successful call added refs on both "key" and "value", owned by the
       dictionary.
       We must now drop our references on them:
    */
    Py_DECREF(key);
    Py_DECREF(value);

    return dict;

 error:
    Py_XDECREF(dict);
    Py_XDECREF(key);
    Py_XDECREF(value);
    return NULL;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
