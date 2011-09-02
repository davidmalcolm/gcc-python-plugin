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

#define MY_INT_MACRO     (42)
#define MY_STRING_MACRO  ("Arthur")

static PyMODINIT_FUNC PyInit_example(void)
{
    PyObject *m;
    PyObject *obj;
#if PY_MAJOR_VERSION == 3
    m = PyModule_Create(&example_module_def);
#else
    m = Py_InitModule("example", ExampleMethods);
#endif

    if (!m) {
        goto error;
    }

    /* Exercise the various PyModule_Add* entrypoints: */
    obj = PyDict_New();
    if (!obj) {
        goto error;
    }

    /* We now own a ref on "obj", which PyModule_AddObject steals: */
    if (-1 == PyModule_AddObject(m, "obj", obj)) {
        Py_DECREF(obj);
        goto error;
    }

    PyModule_AddIntConstant(m, "int_constant", 42);
    PyModule_AddStringConstant(m, "string_constant", "Marvin");
    PyModule_AddIntMacro(m, MY_INT_MACRO);
    PyModule_AddStringMacro(m, MY_STRING_MACRO);

    error:
#if PY_MAJOR_VERSION == 3
    return m;
#else
    (void)0; /* to avoid "label at end of compound statement" error */
#endif
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
