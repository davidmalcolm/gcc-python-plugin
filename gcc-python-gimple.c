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
#include "gcc-python.h"
#include "gcc-python-wrappers.h"
#include "gcc-python-compat.h"
#include "gcc-python-closure.h"
#include "gimple.h"
#include "tree-flow.h"
#include "tree-flow-inline.h"

static PyObject *
do_pretty_print(struct PyGccGimple * self, int spc, int flags)
{
    PyObject *ppobj = gcc_python_pretty_printer_new();
    PyObject *result = NULL;
    if (!ppobj) {
	return NULL;
    }

    dump_gimple_stmt(gcc_python_pretty_printer_as_pp(ppobj),
		     self->stmt,
		     spc, flags);
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
gcc_Gimple_repr(struct PyGccGimple * self)
{
    return gcc_python_string_from_format("%s()", Py_TYPE(self)->tp_name);
}

PyObject *
gcc_Gimple_str(struct PyGccGimple * self)
{
    return do_pretty_print(self, 0, 0);
}

static tree
gimple_walk_tree_callback(tree *tree_ptr, int *walk_subtrees, void *data)
{
    struct walk_stmt_info *wi = (struct walk_stmt_info*)data;
    struct callback_closure *closure = (struct callback_closure *)wi->info;
    PyObject *tree_obj = NULL;
    PyObject *args = NULL;
    PyObject *result = NULL;

    assert(closure);
    assert(*tree_ptr);
    tree_obj = gcc_python_make_wrapper_tree(*tree_ptr);
    if (!tree_obj) {
        goto error;
    }

    args = gcc_python_closure_make_args(closure, 0, tree_obj);
    if (!args) {
        goto error;
    }

    /* Invoke the python callback: */
    result = PyObject_Call(closure->callback, args, closure->kwargs);
    if (!result) {
        goto error;
    }

    if (PyObject_IsTrue(result)) {
        Py_DECREF(result);
        return *tree_ptr;
    } else {
        Py_DECREF(result);
        return NULL;
    }

 error:
    /* On an exception, terminate the traversal: */
    *walk_subtrees = 0;
    Py_XDECREF(tree_obj);
    Py_XDECREF(args);
    Py_XDECREF(result);
    return NULL;
}

PyObject *
gcc_Gimple_walk_tree(struct PyGccGimple * self, PyObject *args, PyObject *kwargs)
{
    PyObject *callback;
    PyObject *extraargs = NULL;
    struct callback_closure *closure;
    tree result;
    struct walk_stmt_info wi;

    callback = PyTuple_GetItem(args, 0);
    extraargs = PyTuple_GetSlice(args, 1, PyTuple_Size(args));

    closure = gcc_python_closure_new_generic(callback, extraargs, kwargs);
    if (!closure) {
        return NULL;
    }

    memset(&wi, 0, sizeof(wi));
    wi.info = closure;

    result = walk_gimple_op (self->stmt,
                             gimple_walk_tree_callback,
                             &wi);
    Py_DECREF(closure);

    /* Propagate exceptions: */
    if (PyErr_Occurred()) {
        return NULL;
    }

    return gcc_python_make_wrapper_tree(result);
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
gcc_Gimple_get_str_no_uid(struct PyGccGimple *self, void *closure)
{
    return do_pretty_print(self, 0, TDF_NOUID);
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

PyObject *
gcc_GimplePhi_get_args(struct PyGccGimple *self, void *closure)
{
    /* See e.g. gimple-pretty-print.c:dump_gimple_phi */
    PyObject * result = NULL;
    int num_args = gimple_phi_num_args (self->stmt);
    int i;

    result = PyList_New(num_args);
    if (!result) {
        goto error;
    }

    for (i = 0 ; i < num_args; i++) {
        tree arg_def = gimple_phi_arg_def(self->stmt, i);
        edge arg_edge = gimple_phi_arg_edge(self->stmt, i);
        /* fwiw, there's also gimple_phi_arg_has_location and gimple_phi_arg_location */
        PyObject *tuple_obj;
        tuple_obj = Py_BuildValue("O&O&",
                                  gcc_python_make_wrapper_tree, arg_def,
                                  gcc_python_make_wrapper_edge, arg_edge);
        if (!tuple_obj) {
            goto error;
        }
        PyList_SET_ITEM(result, i, tuple_obj);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

PyObject *
gcc_GimpleSwitch_get_labels(struct PyGccGimple *self, void *closure)
{
    PyObject * result = NULL;
    unsigned num_labels = gimple_switch_num_labels(self->stmt);
    int i;

    result = PyList_New(num_labels);
    if (!result) {
	goto error;
    }

    for (i = 0 ; i < num_labels; i++) {
	tree t = gimple_switch_label(self->stmt, i);
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


PyObject*
gcc_python_make_wrapper_gimple(gimple stmt)
{
    struct PyGccGimple *gimple_obj = NULL;
    PyTypeObject* tp;
  
    tp = gcc_python_autogenerated_gimple_type_for_stmt(stmt);
    assert(tp);
    //printf("tp:%p\n", tp);
  
    gimple_obj = PyObject_New(struct PyGccGimple, tp);
    if (!gimple_obj) {
        goto error;
    }

    gimple_obj->stmt = stmt;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)gimple_obj;
      
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
