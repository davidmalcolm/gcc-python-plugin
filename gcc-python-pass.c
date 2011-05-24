#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"

/*
  Wrapper for GCC's (opt_pass *)
*/

PyObject *
gcc_Pass_repr(struct PyGccPass *self)
{
     return gcc_python_string_from_format("gcc.%s(name='%s')",
                                          Py_TYPE(self)->tp_name,
                                          self->pass->name);
}

static PyTypeObject *
get_type_for_pass_type(enum opt_pass_type pt)
{
    switch (pt) {
    default: assert(0);

    case GIMPLE_PASS:
	return &gcc_GimplePassType;

    case RTL_PASS:
	return &gcc_RtlPassType;

    case SIMPLE_IPA_PASS:
	return &gcc_SimpleIpaPassType;

    case IPA_PASS:
	return &gcc_IpaPassType;
    }
};


PyObject *
gcc_python_make_wrapper_pass(struct opt_pass *pass)
{
    PyTypeObject *type_obj;
    struct PyGccPass *pass_obj = NULL;

    if (NULL == pass) {
	Py_RETURN_NONE;
    }

    type_obj = get_type_for_pass_type(pass->type);

    pass_obj = PyObject_New(struct PyGccPass, type_obj);
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
indent-tabs-mode: nil
End:
*/
