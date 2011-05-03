#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"

/*
  Wrapper for GCC's (opt_pass *)
*/

PyObject *
gcc_Pass_repr(struct PyGccPass *self)
{
     return PyString_FromFormat("gcc.Pass(name='%s')",
				self->pass->name);
}

PyObject *
gcc_python_make_wrapper_pass(struct opt_pass *pass)
{
    struct PyGccPass *pass_obj = NULL;

    if (NULL == pass) {
	Py_RETURN_NONE;
    }
  
    pass_obj = PyObject_New(struct PyGccPass, &gcc_PassType);
    if (!pass_obj) {
        goto error;
    }

    pass_obj->pass = pass;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)pass_obj;
      
error:
    return NULL;
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
End:
*/
