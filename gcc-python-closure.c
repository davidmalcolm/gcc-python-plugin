#include <Python.h>
#include <gcc-plugin.h>

#include "gcc-python-closure.h"

struct callback_closure *
gcc_python_closure_new(PyObject *callback, PyObject *extraargs)
{
    struct callback_closure *closure;

    assert(callback);
    // extraargs can be NULL

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

    return closure;
}

PyObject *
gcc_python_closure_make_args(struct callback_closure * closure, PyObject *wrapped_gcc_data)
{
    PyObject *args = NULL;
    int i;

    assert(closure);
    /* wrapped_gcc_data can be NULL if there isn't one for this kind of callback */
    assert(closure->extraargs);
    assert(PyTuple_Check(closure->extraargs));
    
    if (wrapped_gcc_data) {
 	/* 
	   Equivalent to:
	     args = (gcc_data, ) + extraargs
	 */
        args = PyTuple_New(1 + PyTuple_Size(closure->extraargs));

	if (!args) {
	    goto error;
	}

	PyTuple_SetItem(args, 0, wrapped_gcc_data);
	Py_INCREF(wrapped_gcc_data);
	for (i = 0; i < PyTuple_Size(closure->extraargs); i++) {
	    PyObject *item = PyTuple_GetItem(closure->extraargs, i);
	    PyTuple_SetItem(args, i + 1, item);
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
    return NULL;
}
