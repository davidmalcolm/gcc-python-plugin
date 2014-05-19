/*
   Copyright 2011, 2012, 2013 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011, 2012, 2013 Red Hat, Inc.

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

/* gimple_phi_arg_def etc were in tree-flow-inline.h prior to 4.9, when they
   moved to gimple.h  */
#if (GCC_VERSION < 4009)
#include "tree-flow.h"
#include "tree-flow-inline.h"
#endif

/*
   Needed for pp_gimple_stmt_1 for gcc 4.8+;
   this header didn't exist in gcc 4.6:
 */
#if (GCC_VERSION >= 4008)
#include "gimple-pretty-print.h"
#endif

#include "gcc-c-api/gcc-gimple.h"

/* GCC 4.9 moved struct walk_stmt_info into the new header gimple-walk.h,
   which in turn needs the new header gimple-iterator.h: */
#if (GCC_VERSION >= 4009)
#include "gimple-iterator.h"
#include "gimple-walk.h"
#endif

gcc_gimple_asm
PyGccGimple_as_gcc_gimple_asm(struct PyGccGimple *self)
{
    return gcc_gimple_as_gcc_gimple_asm(self->stmt);
}

gcc_gimple_assign
PyGccGimple_as_gcc_gimple_assign(struct PyGccGimple *self)
{
    return gcc_gimple_as_gcc_gimple_assign(self->stmt);
}

gcc_gimple_call
PyGccGimple_as_gcc_gimple_call(struct PyGccGimple *self)
{
    return gcc_gimple_as_gcc_gimple_call(self->stmt);
}

gcc_gimple_return
PyGccGimple_as_gcc_gimple_return(struct PyGccGimple *self)
{
    return gcc_gimple_as_gcc_gimple_return(self->stmt);
}

gcc_gimple_cond
PyGccGimple_as_gcc_gimple_cond(struct PyGccGimple *self)
{
    return gcc_gimple_as_gcc_gimple_cond(self->stmt);
}

gcc_gimple_phi
PyGccGimple_as_gcc_gimple_phi(struct PyGccGimple *self)
{
    return gcc_gimple_as_gcc_gimple_phi(self->stmt);
}

gcc_gimple_switch
PyGccGimple_as_gcc_gimple_switch(struct PyGccGimple *self)
{
    return gcc_gimple_as_gcc_gimple_switch(self->stmt);
}

gcc_gimple_label
PyGccGimple_as_gcc_gimple_label(struct PyGccGimple *self)
{
    return gcc_gimple_as_gcc_gimple_label(self->stmt);
}

static PyObject *
do_pretty_print(struct PyGccGimple * self, int spc, int flags)
{
    PyObject *ppobj = PyGccPrettyPrinter_New();
    PyObject *result = NULL;
    if (!ppobj) {
	return NULL;
    }

    /*
      gcc 4.8 renamed "dump_gimple_stmt" to "pp_gimple_stmt_1"
      (in r191884).  Declaration is in gimple-pretty-print.h
    */
#if (GCC_VERSION >= 4008)
    pp_gimple_stmt_1(PyGccPrettyPrinter_as_pp(ppobj),
                     self->stmt.inner,
                     spc, flags);
#else
    dump_gimple_stmt(PyGccPrettyPrinter_as_pp(ppobj),
                     self->stmt.inner,
                     spc, flags);
#endif

    result = PyGccPrettyPrinter_as_string(ppobj);
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
PyGccGimple_repr(struct PyGccGimple * self)
{
    return PyGccString_FromFormat("%s()", Py_TYPE(self)->tp_name);
}

PyObject *
PyGccGimple_str(struct PyGccGimple * self)
{
    return do_pretty_print(self, 0, 0);
}

long
PyGccGimple_hash(struct PyGccGimple * self)
{
    return (long)self->stmt.inner;
}

PyObject *
PyGccGimple_richcompare(PyObject *o1, PyObject *o2, int op)
{
    struct PyGccGimple *gimpleobj1;
    struct PyGccGimple *gimpleobj2;
    int cond;
    PyObject *result_obj;

    if (!PyObject_TypeCheck(o1, (PyTypeObject*)&PyGccGimple_TypeObj)) {
	result_obj = Py_NotImplemented;
	goto out;
    }
    if (!PyObject_TypeCheck(o2, (PyTypeObject*)&PyGccGimple_TypeObj)) {
	result_obj = Py_NotImplemented;
	goto out;
    }

    gimpleobj1 = (struct PyGccGimple *)o1;
    gimpleobj2 = (struct PyGccGimple *)o2;

    switch (op) {
    case Py_EQ:
	cond = (gimpleobj1->stmt.inner == gimpleobj2->stmt.inner);
	break;

    case Py_NE:
	cond = (gimpleobj1->stmt.inner != gimpleobj2->stmt.inner);
	break;

    default:
        result_obj = Py_NotImplemented;
        goto out;
    }
    result_obj = cond ? Py_True : Py_False;

 out:
    Py_INCREF(result_obj);
    return result_obj;
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
    tree_obj = PyGccTree_New(gcc_private_make_tree(*tree_ptr));
    if (!tree_obj) {
        goto error;
    }

    args = PyGcc_Closure_MakeArgs(closure, 0, tree_obj);
    if (!args) {
        goto error;
    }

    /* Invoke the python callback: */
    result = PyObject_Call(closure->callback, args, closure->kwargs);
    if (!result) {
        goto error;
    }

    Py_DECREF(tree_obj);
    Py_DECREF(args);

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
PyGccGimple_walk_tree(struct PyGccGimple * self, PyObject *args, PyObject *kwargs)
{
    PyObject *callback;
    PyObject *extraargs = NULL;
    struct callback_closure *closure;
    tree result;
    struct walk_stmt_info wi;

    callback = PyTuple_GetItem(args, 0);
    extraargs = PyTuple_GetSlice(args, 1, PyTuple_Size(args));

    closure = PyGcc_closure_new_generic(callback, extraargs, kwargs);
    if (!closure) {
        Py_DECREF(callback);
        Py_DECREF(extraargs);
        return NULL;
    }

    memset(&wi, 0, sizeof(wi));
    wi.info = closure;

    result = walk_gimple_op (self->stmt.inner,
                             gimple_walk_tree_callback,
                             &wi);

    PyGcc_closure_free(closure);

    /* Propagate exceptions: */
    if (PyErr_Occurred()) {
        return NULL;
    }

    return PyGccTree_New(gcc_private_make_tree(result));
}

PyObject *
PyGccGimple_get_rhs(struct PyGccGimple *self, void *closure)
{
    PyObject * result = NULL;
    unsigned int i;

    assert(gimple_has_ops(self->stmt.inner));

    assert(gimple_num_ops(self->stmt.inner) > 0);
    result = PyList_New(gimple_num_ops (self->stmt.inner) - 1);
    if (!result) {
	goto error;
    }
    
    for (i = 1 ; i < gimple_num_ops(self->stmt.inner); i++) {
	tree t = gimple_op(self->stmt.inner, i);
	PyObject *obj = PyGccTree_New(gcc_private_make_tree(t));
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
PyGccGimple_get_str_no_uid(struct PyGccGimple *self, void *closure)
{
    return do_pretty_print(self, 0, TDF_NOUID);
}

IMPL_APPENDER(add_tree_to_list,
              gcc_tree,
              PyGccTree_New)

PyObject *
PyGccGimpleCall_get_args(struct PyGccGimple *self, void *closure)
{
    IMPL_LIST_MAKER(gcc_gimple_call_for_each_arg,
                    PyGccGimple_as_gcc_gimple_call(self),
                    add_tree_to_list)
}

PyObject *
PyGccGimpleLabel_repr(PyObject *self)
{
    PyObject *label_repr = NULL;
    PyObject *result = NULL;

    label_repr = PyGcc_GetReprOfAttribute(self, "label");
    if (!label_repr) {
        goto cleanup;
    }

    result = PyGccString_FromFormat("%s(label=%s)",
                                           Py_TYPE(self)->tp_name,
                                           PyGccString_AsString(label_repr));

 cleanup:
    Py_XDECREF(label_repr);

    return result;
}


PyObject *
PyGccGimplePhi_get_args(struct PyGccGimple *self, void *closure)
{
    /* See e.g. gimple-pretty-print.c:dump_gimple_phi */
    PyObject * result = NULL;
    int num_args = gimple_phi_num_args (self->stmt.inner);
    int i;

    result = PyList_New(num_args);
    if (!result) {
        goto error;
    }

    for (i = 0 ; i < num_args; i++) {
        tree arg_def = gimple_phi_arg_def(self->stmt.inner, i);
        edge arg_edge = gimple_phi_arg_edge(self->stmt.inner, i);
        /* fwiw, there's also gimple_phi_arg_has_location and gimple_phi_arg_location */
        PyObject *tuple_obj;
        tuple_obj = Py_BuildValue("O&O&",
                                  PyGccTree_New, arg_def,
                                  PyGccEdge_New, arg_edge);
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

IMPL_APPENDER(add_case_label_expr_to_list,
              gcc_case_label_expr,
              PyGccCaseLabelExpr_New)

PyObject *
PyGccGimpleSwitch_get_labels(struct PyGccGimple *self, void *closure)
{
    IMPL_LIST_MAKER(gcc_gimple_switch_for_each_label,
                    PyGccGimple_as_gcc_gimple_switch(self),
                    add_case_label_expr_to_list)
}


/*
   Ensure we have a unique PyGccGimple per gimple address (by maintaining a dict):
*/
static PyObject *gimple_wrapper_cache = NULL;

union gcc_gimple_or_ptr {
    gcc_gimple stmt;
    void *ptr;
};

static PyObject *
real_make_gimple_wrapper(void *ptr)
{
    union gcc_gimple_or_ptr u;
    u.ptr = ptr;
    struct PyGccGimple *gimple_obj = NULL;
    PyGccWrapperTypeObject* tp;
  
    tp = PyGcc_autogenerated_gimple_type_for_stmt(u.stmt);
    assert(tp);
    //printf("tp:%p\n", tp);
  
    gimple_obj = PyGccWrapper_New(struct PyGccGimple, tp);
    if (!gimple_obj) {
        goto error;
    }

    gimple_obj->stmt = u.stmt;

    return (PyObject*)gimple_obj;
      
error:
    return NULL;
}

PyObject*
PyGccGimple_New(gcc_gimple stmt)
{
    union gcc_gimple_or_ptr u;
    u.stmt = stmt;
    return PyGcc_LazilyCreateWrapper(&gimple_wrapper_cache,
					    u.ptr,
					    real_make_gimple_wrapper);
}

void
PyGcc_WrtpMarkForPyGccGimple(PyGccGimple *wrapper)
{
    gcc_gimple_mark_in_use(wrapper->stmt);
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
