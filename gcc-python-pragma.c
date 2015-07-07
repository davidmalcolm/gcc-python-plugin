// TODO: copyright stuff

#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"

#include "plugin.h"
#include <c-family/c-pragma.h> 

void pragma_callback(struct cpp_reader * cpp_reader, void * data) {
    PyObject * callback = (PyObject *) data;
    PyObject_CallObject(callback, NULL);
}

PyObject*
PyGcc_CRegisterPragma(PyObject *self, PyObject *args)
{
    printf("%s\n", __FUNCTION__);

    const char *directive_space = NULL;
    const char *directive = NULL;
    PyObject *callback = NULL;
    //PyObject dummy;

    if (!PyArg_ParseTuple(args,
                          "ssO:c_register_pragma",
                          &directive_space,
                          &directive,
                          &callback)) {
        return NULL;
    }

    c_register_pragma_with_data(directive_space, directive, pragma_callback, (void *) callback);

    Py_RETURN_NONE;
}
