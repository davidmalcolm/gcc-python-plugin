#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"

PyObject *
gcc_python_make_wrapper_variable(struct varpool_node *node)
{
    struct PyGccVariable *var_obj = NULL;

    if (NULL == node) {
	Py_RETURN_NONE;
    }
  
    var_obj = PyObject_New(struct PyGccVariable, &gcc_VariableType);
    if (!var_obj) {
        goto error;
    }

    var_obj->var = node;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)var_obj;
      
error:
    return NULL;
}


/*
  PEP-7  
Local variables:
c-basic-offset: 4
End:
*/
