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
  Test of correct reference-handling in usage of the PyStructSequence API
*/

#include <Python.h>
#include <structseq.h> /* not pulled in by Python.h */

static struct PyStructSequence_Field coord_fields[] = {
    {"x", NULL},
    {"y", NULL},
    {0}
};

static struct PyStructSequence_Desc coord_desc = {
    "Coord", /* name */
    NULL, /* doc */
    coord_fields,
    2
};

PyTypeObject CoordType;

PyObject *
test(PyObject *self, PyObject *args)
{
    /*
       FWIW, this assumes that we called:
         PyStructSequence_InitType(&CoordType, &coord_desc);
       when initializing the module:
    */
    PyObject *obj = PyStructSequence_New(&CoordType);
    if (!obj) {
        return NULL;
    }

    /*
       These PyInt_ calls can't fail; the SET_ITEM macros steal the new ref
       they give us, so this is correct:
    */
    PyStructSequence_SET_ITEM(obj, 0, PyInt_FromLong(0));
    PyStructSequence_SET_ITEM(obj, 1, PyInt_FromLong(0));
    return obj;
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
