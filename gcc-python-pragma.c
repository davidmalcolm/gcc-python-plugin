/*
   FIXME: copyright stuff
   FIXME: implement support for c_register_pragma_with_data,
          c_register_pragma_with_expansion,
          c_register_pragma_with_expansion_and_data
 */

#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"

#include "plugin.h"
#include <c-family/c-pragma.h> 

void handle_python_pragma(struct cpp_reader *cpp_reader, void *data) {
    PyObject * callback = (PyObject*)data;

    /* Debug code: */
    if (0) {
        printf("handle_python_pragma called\n");
        fprintf(stderr, "cpp_reader: %p\n", cpp_reader);
    }

    PyObject_CallObject(callback, NULL);
}

PyObject*
PyGcc_CRegisterPragma(PyObject *self, PyObject *args)
{
    const char *directive_space = NULL;
    const char *directive = NULL;
    PyObject *callback = NULL;

    if (!PyArg_ParseTuple(args,
                          "ssO:c_register_pragma",
                          &directive_space,
                          &directive,
                          &callback)) {
        return NULL;
    }

    c_register_pragma_with_data(directive_space, directive, pragma_callback, (void*)callback);

    Py_RETURN_NONE;
}
