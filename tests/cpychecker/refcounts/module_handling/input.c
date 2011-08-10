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
  Verify that the checker can cope with module creation
*/
static PyMethodDef ExampleMethods[] = {
    /* Sentinel: */
    {NULL, NULL, 0, NULL}
};

#if PY_MAJOR_VERSION == 3
static struct PyModuleDef example_module_def = {
    PyModuleDef_HEAD_INIT,
    "example",   /* name of module */
    NULL,
    -1,
    ExampleMethods
};
#endif

static PyMODINIT_FUNC PyInit_example(void)
{
    PyObject *m;
#if PY_MAJOR_VERSION == 3
    m = PyModule_Create(&example_module_def);
#else
    m = Py_InitModule("example", ExampleMethods);
#endif

#if PY_MAJOR_VERSION == 3
    return m;
#endif
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
