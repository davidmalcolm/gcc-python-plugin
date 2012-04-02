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
#include "proposed-plugin-api/gcc-cfg.h"
#include "proposed-plugin-api/gcc-gimple.h"

#if 1
/* Ideally we wouldn't have these includes here: */
#include "basic-block.h"
#include "rtl.h"
#endif

/*
  "struct edge_def" is declared in basic-block.h, c.f:
      struct GTY(()) edge_def {
           ... snip ...
      }
  and there are these typedefs to pointers defined in coretypes.h:
      typedef struct edge_def *edge;
      typedef const struct edge_def *const_edge;
 */
PyObject *
gcc_python_make_wrapper_edge(gcc_cfg_edge e)
{
    struct PyGccEdge *obj;

    if (!e.inner) {
	Py_RETURN_NONE;
    }

    obj = PyGccWrapper_New(struct PyGccEdge, &gcc_EdgeType);
    if (!obj) {
        goto error;
    }

    obj->e = e;

    return (PyObject*)obj;
      
error:
    return NULL;
}

void
wrtp_mark_for_PyGccEdge(PyGccEdge *wrapper)
{
    /* Mark the underlying object (recursing into its fields): */
    gcc_cfg_edge_mark_in_use(wrapper->e);
}

static bool add_edge_to_list(gcc_cfg_edge edge, void *user_data)
{
    PyObject *result = (PyObject*)user_data;
    PyObject *item;

    item = gcc_python_make_wrapper_edge(edge);
    if (!item) {
        return true;
    }

    if (-1 == PyList_Append(result, item)) {
        Py_DECREF(item);
        return true;
    }

    /* Success: */
    Py_DECREF(item);
    return false;
}

PyObject *
gcc_BasicBlock_get_preds(PyGccBasicBlock *self, void *closure)
{
    PyObject *result;

    result = PyList_New(0);
    if (!result) {
        return NULL;
    }

    if (gcc_cfg_block_for_each_pred_edge(self->bb,
                                     add_edge_to_list,
                                     result)) {
        Py_DECREF(result);
        return NULL;
    }

    return result;
}

PyObject *
gcc_BasicBlock_get_succs(PyGccBasicBlock *self, void *closure)
{
    PyObject *result;

    result = PyList_New(0);
    if (!result) {
        return NULL;
    }

    if (gcc_cfg_block_for_each_succ_edge(self->bb,
                                     add_edge_to_list,
                                     result)) {
        Py_DECREF(result);
        return NULL;
    }

    return result;
}

static bool
append_gimple_to_list(gcc_gimple stmt, void *user_data)
{
    PyObject *result = (PyObject *)user_data;
    PyObject *obj_stmt;

    obj_stmt = gcc_python_make_wrapper_gimple(stmt);
    if (!obj_stmt) {
        return true;
    }

    if (PyList_Append(result, obj_stmt)) {
        Py_DECREF(obj_stmt);
        return true;
    }

    /* Success: */
    Py_DECREF(obj_stmt);
    return false;
}

PyObject *
gcc_BasicBlock_get_gimple(PyGccBasicBlock *self, void *closure)
{
    PyObject *result = NULL;

    assert(self);
    assert(self->bb.inner);

    result = PyList_New(0);
    if (!result) {
        return NULL;
    }

    if (gcc_cfg_block_for_each_gimple(self->bb,
                                   append_gimple_to_list,
                                   result)) {
        Py_DECREF(result);
        return NULL;
    }

    return result;
}

static bool
append_gimple_phi_to_list(gcc_gimple_phi stmt, void *user_data)
{
    PyObject *result = (PyObject *)user_data;
    PyObject *obj_stmt;

    obj_stmt = gcc_python_make_wrapper_gimple(gcc_gimple_phi_upcast(stmt));
    if (!obj_stmt) {
        return true;
    }

    if (PyList_Append(result, obj_stmt)) {
        Py_DECREF(obj_stmt);
        return true;
    }

    /* Success: */
    Py_DECREF(obj_stmt);
    return false;
}

PyObject *
gcc_BasicBlock_get_phi_nodes(PyGccBasicBlock *self, void *closure)
{
    PyObject *result = NULL;

    assert(self);
    assert(self->bb.inner);

    result = PyList_New(0);
    if (!result) {
        return NULL;
    }

    if (gcc_cfg_block_for_each_gimple_phi(self->bb,
                                      append_gimple_phi_to_list,
                                      result)) {
        Py_DECREF(result);
        return NULL;
    }

    return result;
}

static bool
append_rtl_to_list(gcc_rtl_insn insn, void *user_data)
{
    PyObject *result = (PyObject *)user_data;
    PyObject *obj;

    obj = gcc_python_make_wrapper_rtl(insn);
    if (!obj) {
        return true;
    }

    if (PyList_Append(result, obj)) {
        Py_DECREF(obj);
        return true;
    }

    /* Success: */
    Py_DECREF(obj);
    return false;
}

PyObject *
gcc_BasicBlock_get_rtl(PyGccBasicBlock *self, void *closure)
{
    PyObject *result = NULL;

    assert(self);
    assert(self->bb.inner);

    result = PyList_New(0);
    if (!result) {
        return NULL;
    }

    if (gcc_cfg_block_for_each_rtl_insn(self->bb,
                                    append_rtl_to_list,
                                    result)) {
        Py_DECREF(result);
        return NULL;
    }

    return result;
}


/*
  Force a 1-1 mapping between pointer values and wrapper objects
 */
PyObject *
gcc_python_lazily_create_wrapper(PyObject **cache,
				 void *ptr,
				 PyObject *(*ctor)(void *ptr))
{
    PyObject *key = NULL;
    PyObject *oldobj = NULL;
    PyObject *newobj = NULL;

    /* printf("gcc_python_lazily_create_wrapper(&%p, %p, %p)\n", *cache, ptr, ctor); */

    assert(cache);
    /* ptr is allowed to be NULL */
    assert(ctor);

    /* The cache is lazily created: */
    if (!*cache) {
	*cache = PyDict_New();
	if (!*cache) {
	    return NULL;
	}
    }

    key = PyLong_FromVoidPtr(ptr);
    if (!key) {
	return NULL;
    }

    oldobj = PyDict_GetItem(*cache, key);
    if (oldobj) {
	/* The cache already contains an object wrapping "ptr": reuse t */
	/* printf("reusing %p for %p\n", oldobj, ptr); */
	Py_INCREF(oldobj); /* it was a borrowed ref */
	Py_DECREF(key);
	return oldobj;
    }

    /* 
       Not in the cache: we don't yet have a wrapper object for this pointer
    */
       
    assert(NULL != key); /* we own a ref */
    assert(NULL == oldobj);
    assert(NULL == newobj);

    /* Construct a wrapper : */

    newobj = (*ctor)(ptr);
    if (!newobj) {
	Py_DECREF(key);
	return NULL;
    }

    /* printf("created %p for %p\n", newobj, ptr); */

    if (PyDict_SetItem(*cache, key, newobj)) {
	Py_DECREF(newobj);
	Py_DECREF(key);
	return NULL;
    }

    Py_DECREF(key);
    return newobj;
}

int
gcc_python_insert_new_wrapper_into_cache(PyObject **cache,
                                         void *ptr,
                                         PyObject *obj)
{
    PyObject *key;
    assert(cache);
    assert(ptr);
    assert(obj);

    /* The cache is lazily created: */
    if (!*cache) {
	*cache = PyDict_New();
	if (!*cache) {
	    return -1;
	}
    }

    key = PyLong_FromVoidPtr(ptr);
    if (!key) {
	return -1;
    }

    if (PyDict_SetItem(*cache, key, obj)) {
	Py_DECREF(key);
	return -1;
    }

    Py_DECREF(key);
    return 0;
}

static PyObject *
real_make_basic_block_wrapper(void *ptr)
{
    gcc_cfg_block bb = gcc_private_make_cfg_block(ptr);
    struct PyGccBasicBlock *obj;

    if (!bb.inner) {
	Py_RETURN_NONE;
    }

    obj = PyGccWrapper_New(struct PyGccBasicBlock, &gcc_BasicBlockType);
    if (!obj) {
        goto error;
    }

#if 0
    printf("bb: %p\n", bb);
    printf("bb->flags: 0x%x\n", bb->flags);
    printf("bb->flags & BB_RTL: %i\n", bb->flags & BB_RTL);
    if (bb->flags & BB_RTL) {
	printf("bb->il.rtl: %p\n", bb->il.rtl);
    } else {
	printf("bb->il.gimple: %p\n", bb->il.gimple);
	if (bb->il.gimple) {
	    /* 
	       See http://gcc.gnu.org/onlinedocs/gccint/GIMPLE.html
	       and also gimple-pretty-print.c

	       coretypes.h has:
	           struct gimple_seq_d;
		   typedef struct gimple_seq_d *gimple_seq;

	       and gimple.h has:
   	           "A double-linked sequence of gimple statements."
		   struct GTY ((chain_next ("%h.next_free"))) gimple_seq_d {
                        ... snip ...
		   }
               and:
		   struct gimple_seq_node_d;
		   typedef struct gimple_seq_node_d *gimple_seq_node;
	       and:
	           struct GTY((chain_next ("%h.next"), chain_prev ("%h.prev"))) gimple_seq_node_d {
		       gimple stmt;
		       struct gimple_seq_node_d *prev;
		       struct gimple_seq_node_d *next;
		   };
	       and coretypes.h has:
	           union gimple_statement_d;
		   typedef union gimple_statement_d *gimple;
	       and gimple.h has the "union gimple_statement_d", and another
	       set of codes for this
	    */

	    printf("bb->il.gimple->seq: %p\n", bb->il.gimple->seq);
	    printf("bb->il.gimple->phi_nodes: %p\n", bb->il.gimple->phi_nodes);

	    {
		gimple_stmt_iterator i;
		
		for (i = gsi_start (bb->il.gimple->seq); !gsi_end_p (i); gsi_next (&i)) {
		    gimple stmt = gsi_stmt(i);
		    printf("  gimple: %p code: %s (%i) %s:%i num_ops=%i\n", 
			   stmt,
			   gimple_code_name[gimple_code(stmt)],
			   gimple_code(stmt),
			   gimple_filename(stmt),
			   gimple_lineno(stmt),
			   gimple_num_ops(stmt));
		    //print_generic_stmt (stderr, stmt, 0);
		}
	    }

	}
    }
#endif

    obj->bb = bb;

    return (PyObject*)obj;
      
error:
    return NULL;
}

void
wrtp_mark_for_PyGccBasicBlock(PyGccBasicBlock *wrapper)
{
    /* Mark the underlying object (recursing into its fields): */
    gcc_cfg_block_mark_in_use(wrapper->bb);
}


static PyObject *basic_block_wrapper_cache = NULL;
PyObject *
gcc_python_make_wrapper_basic_block(gcc_cfg_block bb)
{
    return gcc_python_lazily_create_wrapper(&basic_block_wrapper_cache,
					    bb.inner,
					    real_make_basic_block_wrapper);
}

static bool add_block_to_list(gcc_cfg_block block, void *user_data)
{
    PyObject *result = (PyObject*)user_data;
    PyObject *item;

    item = gcc_python_make_wrapper_basic_block(block);
    if (!item) {
        return true;
    }

    if (-1 == PyList_Append(result, item)) {
        Py_DECREF(item);
        return true;
    }

    /* Success: */
    Py_DECREF(item);
    return false;
}

PyObject *
gcc_Cfg_get_basic_blocks(PyGccCfg *self, void *closure)
{
    PyObject *result;
    
    result = PyList_New(0);
    if (!result) {
	return NULL;
    }

    if (gcc_cfg_for_each_block(self->cfg,
                             add_block_to_list,
                             result)) {
        Py_DECREF(result);
        return NULL;
    }

    return result;
}

extern PyTypeObject gcc_LabelDeclType;

PyObject *
gcc_Cfg_get_block_for_label(PyObject *s, PyObject *args)
{
    struct PyGccCfg *self = (struct PyGccCfg *)s;
    struct PyGccTree *label_decl;
    int uid;
    basic_block bb;

    if (!PyArg_ParseTuple(args,
                          "O!:get_block_for_label",
                          &gcc_LabelDeclType, &label_decl)) {
        return NULL;
    }

    /* See also gcc/tree-cfg.c: label_to_block_fn */
    uid = LABEL_DECL_UID(label_decl->t);

    if (uid < 0 ||
        (VEC_length (basic_block, self->cfg.inner->x_label_to_block_map)
         <=
         (unsigned int) uid)
        ) {
        return PyErr_Format(PyExc_ValueError,
                            "uid %i not found", uid);
    }

    bb = VEC_index(basic_block, self->cfg.inner->x_label_to_block_map, uid);

    return gcc_python_make_wrapper_basic_block(gcc_private_make_cfg_block(bb));
}

PyObject *
gcc_python_make_wrapper_cfg(gcc_cfg cfg)
{
    struct PyGccCfg *obj;

    if (!cfg.inner) {
	Py_RETURN_NONE;
    }

    obj = PyGccWrapper_New(struct PyGccCfg, &gcc_CfgType);
    if (!obj) {
        goto error;
    }

    obj->cfg = cfg;

    return (PyObject*)obj;
      
error:
    return NULL;
}

void
wrtp_mark_for_PyGccCfg(PyGccCfg *wrapper)
{
    /* Mark the underlying object (recursing into its fields): */
    gcc_cfg_mark_in_use(wrapper->cfg);
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
