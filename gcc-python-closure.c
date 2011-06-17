#include <Python.h>
#include <gcc-plugin.h>

#include "gcc-python-closure.h"
#include "gcc-python.h"
#include "function.h"

struct callback_closure *
gcc_python_closure_new(PyObject *callback, PyObject *extraargs, PyObject *kwargs)
{
    struct callback_closure *closure;

    assert(callback);
    /* extraargs can be NULL
       kwargs can also be NULL */

    closure = PyMem_New(struct callback_closure, 1);
    if (!closure) {
        return NULL;
    }
    
    closure->callback = callback;

    // FIXME: we may want to pass in the event enum as well as the user-supplied extraargs

    if (extraargs) {
	/* Hold a reference to the extraargs for when we register it with the
	   callback: */
	closure->extraargs = extraargs;
	Py_INCREF(extraargs);
    } else {
	closure->extraargs = PyTuple_New(0);
	if (!closure->extraargs) {
	    return NULL;  // singleton, so can't happen, really
	}
    }

    closure->kwargs = kwargs;
    if (kwargs) {
	Py_INCREF(kwargs);
    }

    return closure;
}

PyObject *
gcc_python_closure_make_args(struct callback_closure * closure, PyObject *wrapped_gcc_data)
{
    PyObject *args = NULL;
    PyObject *cfun_obj = NULL;
    int i;

    assert(closure);
    /* wrapped_gcc_data can be NULL if there isn't one for this kind of callback */
    assert(closure->extraargs);
    assert(PyTuple_Check(closure->extraargs));
    
    if (wrapped_gcc_data) {
 	/* 
	   Equivalent to:
	     args = (gcc_data, cfun, ) + extraargs
	 */
        args = PyTuple_New(2 + PyTuple_Size(closure->extraargs));

	if (!args) {
	    goto error;
	}

	cfun_obj = gcc_python_make_wrapper_function(cfun);
	if (!cfun_obj) {
	    goto error;
	}

	PyTuple_SetItem(args, 0, wrapped_gcc_data);
	PyTuple_SetItem(args, 1, cfun_obj);
	Py_INCREF(wrapped_gcc_data);
	for (i = 0; i < PyTuple_Size(closure->extraargs); i++) {
	    PyObject *item = PyTuple_GetItem(closure->extraargs, i);
	    PyTuple_SetItem(args, i + 2, item);
	    Py_INCREF(item);
	}
	
	return args;
	
    } else {
	/* Just reuse closure's extraargs tuple */
	Py_INCREF(closure->extraargs);
	return closure->extraargs;
    }

 error:
    Py_XDECREF(args);
    Py_XDECREF(cfun_obj);
    return NULL;
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
