#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"
#include "gimple.h"

PyObject *
gcc_Gimple_repr(struct PyGccGimple * self)
{
    return PyString_FromFormat("%s()", Py_TYPE(self)->tp_name);
}

/* FIXME:
   This is declared in gimple-pretty-print.c, but not exposed in any of the plugin headers AFAIK:
*/
void
dump_gimple_stmt (pretty_printer *buffer, gimple gs, int spc, int flags);

PyObject *
gcc_Gimple_str(struct PyGccGimple * self)
{
    PyObject *ppobj = gcc_python_pretty_printer_new();
    PyObject *result = NULL;
    if (!ppobj) {
	return NULL;
    }

    dump_gimple_stmt(gcc_python_pretty_printer_as_pp(ppobj),
		     self->stmt,
		     0, 0);
    result = gcc_python_pretty_printer_as_string(ppobj);
    if (!result) {
	goto error;
    }
    
    Py_XDECREF(ppobj);
    return result;
    
 error:
    Py_XDECREF(ppobj);
    return NULL;
}

PyObject *
gcc_Gimple_get_rhs(struct PyGccGimple *self, void *closure)
{
    PyObject * result = NULL;
    int i;

    assert(gimple_has_ops(self->stmt));

    assert(gimple_num_ops(self->stmt) > 0);
    result = PyList_New(gimple_num_ops (self->stmt) - 1);
    if (!result) {
	goto error;
    }
    
    for (i = 1 ; i < gimple_num_ops(self->stmt); i++) {
	tree t = gimple_op(self->stmt, i);
	PyObject *obj = gcc_python_make_wrapper_tree(t);
	if (!obj) {
	    goto error;
	}
	PyList_SetItem(result, i-1, obj);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

PyObject *
gcc_GimpleCall_get_args(struct PyGccGimple *self, void *closure)
{
    PyObject * result = NULL;
    int num_args = gimple_call_num_args (self->stmt);
    int i;

    result = PyList_New(num_args);
    if (!result) {
	goto error;
    }
    
    for (i = 0 ; i < num_args; i++) {
	tree t = gimple_call_arg(self->stmt, i);
	PyObject *obj = gcc_python_make_wrapper_tree(t);
	if (!obj) {
	    goto error;
	}
	PyList_SetItem(result, i, obj);
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
End:
*/
