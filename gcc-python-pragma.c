// TODO: copyright stuff

#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"

#include "plugin.h"
#include <c-family/c-pragma.h> 

PyObject*
PyGcc_CRegisterPragma(PyObject *self, PyObject *args, PyObject *kwargs)
{
    const char *directive_space = NULL;
    const char *directive = NULL;
    PyObject *callback = NULL;

    if (!PyArg_ParseTuple(args,
                          "ssO:c_register_pragma",
                          &directive_space,
                          &directive,
                          &callback)) {
        printf("error %s\n", __FUNCTION__);
        return NULL;
    }

    // TODO: error here. how do we pass a python callback to gcc?
    c_register_pragma(directive_space, directive, (pragma_handler_1arg)callback);
    
    Py_RETURN_NONE;
}
