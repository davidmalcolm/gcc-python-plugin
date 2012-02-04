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

const unsigned int unknown_unsigned_val;

extern PyObject*
make_item(int i);

PyObject *
test(PyObject *self, PyObject *args)
{
    PyObject *result;
    int i = 0;

    result = PyList_New(0);
    if (!result) {
	goto error;
    }

    for (i = 0; i < unknown_unsigned_val; i++) {
	PyObject *item = make_item(i);
	if (!item) {
	    goto error;
	}
	if (-1 == PyList_Append(result, item)) {
	    Py_DECREF(item);
	    goto error;
	}
        /* BUG: leak of item here */
        /* Was seeing no traces in which PyList_Append succeeds, due to
           over-aggressive loop-detection.
           The comparison in the loop is 3 statements long:
loc: block 12 stmt:0 :   gcc.GimpleAssign() : i.0 = (unsigned int) i;
loc: block 12 stmt:1 :   gcc.GimpleAssign() : unknown_unsigned_val.1 = unknown_unsigned_val;
loc: block 12 stmt:2 :     gcc.GimpleCond() : if (i.0 < unknown_unsigned_val.1)
        */
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
