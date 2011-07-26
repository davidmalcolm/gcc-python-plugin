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
#include "gimple.h"

//#include "rtl.h"
/*
  "struct rtx_def" is declarted within rtl.h, c.f:
    struct GTY((chain_next ("RTX_NEXT (&%h)"),
	    chain_prev ("RTX_PREV (&%h)"), variable_size)) rtx_def {
           ... snip ...
    }
    
  and seems to be the fundamental instruction type
    
  Seems to use RTX_NEXT() and RTX_PREV()
*/

/*
    Code for various tree types
 */
static PyObject *
do_pretty_print(struct PyGccTree * self, int spc, int flags)
{
    PyObject *ppobj = gcc_python_pretty_printer_new();
    PyObject *result = NULL;
    if (!ppobj) {
	return NULL;
    }

    dump_generic_node (gcc_python_pretty_printer_as_pp(ppobj),
		       self->t, spc, flags, 0);
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
gcc_Tree_str(struct PyGccTree * self)
{
    return do_pretty_print(self, 0, 0);
}

long
gcc_Tree_hash(struct PyGccTree * self)
{
    /* Use the ptr as the hash value: */
    return (long)self->t;
}


PyObject *
gcc_Tree_richcompare(PyObject *o1, PyObject *o2, int op)
{
    struct PyGccTree *treeobj1;
    struct PyGccTree *treeobj2;
    int cond;
    PyObject *result_obj;

    if (!PyObject_TypeCheck(o1, &gcc_TreeType)) {
	result_obj = Py_NotImplemented;
	goto out;
    }
    if (!PyObject_TypeCheck(o2, &gcc_TreeType)) {
	result_obj = Py_NotImplemented;
	goto out;
    }

    treeobj1 = (struct PyGccTree *)o1;
    treeobj2 = (struct PyGccTree *)o2;

    switch (op) {
    case Py_EQ:
	cond = (treeobj1->t == treeobj2->t);
	break;

    case Py_NE:
	cond = (treeobj1->t != treeobj2->t);
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

PyObject *
gcc_Tree_get_str_no_uid(struct PyGccTree *self, void *closure)
{
    return do_pretty_print(self, 0, TDF_NOUID);
}

PyObject *
gcc_Declaration_repr(struct PyGccTree * self)
{
    PyObject *name = NULL;
    PyObject *result = NULL;

    if (DECL_NAME(self->t)) {
	name = gcc_Declaration_get_name(self, NULL);
	if (!name) {
	    goto error;
	}

        result = gcc_python_string_from_format("%s('%s')",
                                               Py_TYPE(self)->tp_name,
                                               gcc_python_string_as_string(name));
	Py_DECREF(name);
    } else {
        result = gcc_python_string_from_format("%s(%u)",
				     Py_TYPE(self)->tp_name,
				     DECL_UID (self->t));
    }

    return result;
error:
    Py_XDECREF(name);
    Py_XDECREF(result);
    return NULL;
}

PyObject *
gcc_FunctionType_get_argument_types(struct PyGccTree * self, void *closure)
{
    PyObject *result;
    PyObject *item;
    int i, size;
    tree iter;
    tree head = TYPE_ARG_TYPES(self->t);

    /* Get length of chain */
    for (size = 0, iter = head;
         iter && iter != error_mark_node;
         iter = TREE_CHAIN(iter), size++) {
        /* empty */
    }

    /* "size" should now be the length of the chain */

    /* The last element in the list is a VOID_TYPE; don't add this;
       see dump_function_declaration() in gcc/tree-pretty-print.c */
    assert(size>0);
    size--;

    result = PyTuple_New(size);
    if (!result) {
        return NULL;
    }

    /* Iterate, but don't visit the final element: */
    for (i = 0, iter = head;
         iter && TREE_CHAIN(iter) && iter != error_mark_node;
         iter = TREE_CHAIN(iter), i++) {

        assert(i<size);

	item = gcc_python_make_wrapper_tree(TREE_VALUE(iter));
	if (!item) {
	    goto error;
	}
	PyTuple_SetItem(result, i, item);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}


PyObject *
gcc_Constructor_get_elements(PyObject *self, void *closure)
{
    struct PyGccTree * self_as_tree;
    PyObject *result = NULL;
    tree node;
    unsigned HOST_WIDE_INT cnt;
    tree index, value;

    self_as_tree = (struct PyGccTree *)self; /* FIXME */
    node = self_as_tree->t;
    
    result = PyList_New(VEC_length(constructor_elt, CONSTRUCTOR_ELTS (node)));
    if (!result) {
	goto error;
    }

    FOR_EACH_CONSTRUCTOR_ELT (CONSTRUCTOR_ELTS (node),
			      cnt, index, value) {
	PyObject *obj_index = NULL;
	PyObject *obj_value = NULL;
	PyObject *obj_pair = NULL;
	obj_index = gcc_python_make_wrapper_tree(index);
	if (!obj_index) {
	    goto error;
	}
	obj_value = gcc_python_make_wrapper_tree(value);
	if (!obj_value) {
	    Py_DECREF(obj_index);
	    goto error;
	}
	obj_pair = PyTuple_Pack(2, obj_index, obj_value);
	if (!obj_pair) {
	    Py_DECREF(obj_value);
	    Py_DECREF(obj_index);
	    goto error;
	}

	if (-1 == PyList_SetItem(result, cnt, obj_pair)) {
	    Py_DECREF(obj_pair);
	    goto error;
	}
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

PyObject *
gcc_IntegerConstant_get_constant(struct PyGccTree * self, void *closure)
{
    tree type = TREE_TYPE(self->t);
    return gcc_python_int_from_double_int(TREE_INT_CST(self->t),
                                          TYPE_UNSIGNED(type));
}

PyObject *
gcc_TypeDecl_get_pointer(struct PyGccTree *self, void *closure)
{
    tree decl_type = TREE_TYPE(self->t);
    if (!decl_type) {
        PyErr_SetString(PyExc_ValueError, "gcc.TypeDecl has no associated type");
        return NULL;
    }
    return gcc_python_make_wrapper_tree(build_pointer_type(decl_type));
}

/* 
   GCC's debug_tree is implemented in:
     gcc/print-tree.c
   e.g. in:
     /usr/src/debug/gcc-4.6.0-20110321/gcc/print-tree.c
   and appears to be a good place to look when figuring out how the tree data
   works.

   dump_generic_node is defined around line 580 of tree-pretty-print.c
*/
static PyObject *
real_make_tree_wrapper(void *t)
{

    struct PyGccTree *tree_obj = NULL;
    PyTypeObject* tp;

    if (NULL == t) {
	Py_RETURN_NONE;
    }
  
    tp = gcc_python_autogenerated_tree_type_for_tree(t, 1);
    assert(tp);
    
    tree_obj = PyObject_New(struct PyGccTree, tp);
    if (!tree_obj) {
        goto error;
    }

    tree_obj->t = t;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)tree_obj;
      
error:
    return NULL;
}

/*
   Ensure we have a unique PyGccTree per tree address (by maintaining a dict)
   (what about lifetimes?)
*/
static PyObject *tree_wrapper_cache = NULL;

PyObject *
gcc_python_make_wrapper_tree(tree t)
{
    return gcc_python_lazily_create_wrapper(&tree_wrapper_cache,
					    t,
					    real_make_tree_wrapper);
}

/* Walk the chain of a tree, building a python list of wrapper gcc.Tree
   instances */
PyObject *
gcc_tree_list_from_chain(tree t)
{
    PyObject *result = NULL;
    
    result = PyList_New(0);
    if (!result) {
	goto error;
    }

    while (t) {
	PyObject *item;
	item = gcc_python_make_wrapper_tree(t);
	if (!item) {
	    goto error;
	}
	if (-1 == PyList_Append(result, item)) {
	    Py_DECREF(item);
	    goto error;
	}
	t = TREE_CHAIN(t);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

PyObject *
VEC_tree_as_PyList(VEC(tree,gc) *vec_nodes)
{
    PyObject *result = NULL;
    int i;
    tree t;

    result = PyList_New(VEC_length(tree, vec_nodes));
    if (!result) {
	goto error;
    }

    FOR_EACH_VEC_ELT(tree, vec_nodes, i, t) {
	PyObject *item;
	item = gcc_python_make_wrapper_tree(t);
	if (!item) {
	    goto error;
	}
	PyList_SetItem(result, i, item);
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
indent-tabs-mode: nil
End:
*/
