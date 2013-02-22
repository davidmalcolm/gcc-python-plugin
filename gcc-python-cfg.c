/*
   Copyright 2011, 2013 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011, 2013 Red Hat, Inc.

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
#include "gcc-c-api/gcc-cfg.h"
#include "gcc-c-api/gcc-gimple.h"

#include "gcc-c-api/gcc-private-compat.h" /* for now */

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

union cfg_edge_or_ptr {
    gcc_cfg_edge edge;
    void *ptr;
};

PyObject *
real_make_edge(void * ptr)
{
    union cfg_edge_or_ptr u;
    u.ptr = ptr;
    struct PyGccEdge *obj;

    if (!u.edge.inner) {
	Py_RETURN_NONE;
    }

    obj = PyGccWrapper_New(struct PyGccEdge, &PyGccEdge_TypeObj);
    if (!obj) {
        goto error;
    }

    obj->e = u.edge;

    return (PyObject*)obj;
      
error:
    return NULL;
}

static PyObject *edge_wrapper_cache = NULL;

PyObject *
PyGccEdge_New(gcc_cfg_edge e)
{
    union cfg_edge_or_ptr u;
    u.edge = e;
    return PyGcc_LazilyCreateWrapper(&edge_wrapper_cache,
					    u.ptr,
					    real_make_edge);
}

void
PyGcc_WrtpMarkForPyGccEdge(PyGccEdge *wrapper)
{
    /* Mark the underlying object (recursing into its fields): */
    gcc_cfg_edge_mark_in_use(wrapper->e);
}

IMPL_APPENDER(add_edge_to_list,
              gcc_cfg_edge,
              PyGccEdge_New)

PyObject *
PyGccBasicBlock_repr(struct PyGccBasicBlock * self)
{
    return PyGccString_FromFormat("%s(index=%i)",
                                         Py_TYPE(self)->tp_name,
                                         gcc_cfg_block_get_index(self->bb));
}

PyObject *
PyGccBasicBlock_get_preds(PyGccBasicBlock *self, void *closure)
{
    IMPL_LIST_MAKER(gcc_cfg_block_for_each_pred_edge,
                    self->bb,
                    add_edge_to_list)
}

PyObject *
PyGccBasicBlock_get_succs(PyGccBasicBlock *self, void *closure)
{
    IMPL_LIST_MAKER(gcc_cfg_block_for_each_succ_edge,
                    self->bb,
                    add_edge_to_list)
}

IMPL_APPENDER(append_gimple_to_list,
              gcc_gimple,
              PyGccGimple_New)

PyObject *
PyGccBasicBlock_get_gimple(PyGccBasicBlock *self, void *closure)
{
    assert(self);
    assert(self->bb.inner);

    IMPL_LIST_MAKER(gcc_cfg_block_for_each_gimple,
                    self->bb,
                    append_gimple_to_list)
}

static PyObject*
PyGccGimple_New_phi(gcc_gimple_phi phi)
{
    return PyGccGimple_New(gcc_gimple_phi_as_gcc_gimple(phi));
}

IMPL_APPENDER(append_gimple_phi_to_list,
              gcc_gimple_phi,
              PyGccGimple_New_phi)

PyObject *
PyGccBasicBlock_get_phi_nodes(PyGccBasicBlock *self, void *closure)
{
    assert(self);
    assert(self->bb.inner);

    IMPL_LIST_MAKER(gcc_cfg_block_for_each_gimple_phi,
                    self->bb,
                    append_gimple_phi_to_list)
}

IMPL_APPENDER(append_rtl_to_list,
              gcc_rtl_insn,
              PyGccRtl_New)

PyObject *
PyGccBasicBlock_get_rtl(PyGccBasicBlock *self, void *closure)
{
    assert(self);
    assert(self->bb.inner);

    IMPL_LIST_MAKER(gcc_cfg_block_for_each_rtl_insn,
                    self->bb,
                    append_rtl_to_list)
}


/*
  Force a 1-1 mapping between pointer values and wrapper objects
 */
PyObject *
PyGcc_LazilyCreateWrapper(PyObject **cache,
				 void *ptr,
				 PyObject *(*ctor)(void *ptr))
{
    PyObject *key = NULL;
    PyObject *oldobj = NULL;
    PyObject *newobj = NULL;

    /* printf("PyGcc_LazilyCreateWrapper(&%p, %p, %p)\n", *cache, ptr, ctor); */

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
PyGcc_insert_new_wrapper_into_cache(PyObject **cache,
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

union cfg_block_or_ptr {
    gcc_cfg_block block;
    void *ptr;
};

static PyObject *
real_make_basic_block_wrapper(void *ptr)
{
    union cfg_block_or_ptr u;
    struct PyGccBasicBlock *obj;

    u.ptr = ptr;

    if (!u.block.inner) {
	Py_RETURN_NONE;
    }

    obj = PyGccWrapper_New(struct PyGccBasicBlock, &PyGccBasicBlock_TypeObj);
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

    obj->bb = u.block;

    return (PyObject*)obj;
      
error:
    return NULL;
}

void
PyGcc_WrtpMarkForPyGccBasicBlock(PyGccBasicBlock *wrapper)
{
    /* Mark the underlying object (recursing into its fields): */
    gcc_cfg_block_mark_in_use(wrapper->bb);
}


static PyObject *basic_block_wrapper_cache = NULL;
PyObject *
PyGccBasicBlock_New(gcc_cfg_block bb)
{
    return PyGcc_LazilyCreateWrapper(&basic_block_wrapper_cache,
					    bb.inner,
					    real_make_basic_block_wrapper);
}

static bool
add_block_to_list(gcc_cfg_block bb, void *user_data)
{
    PyObject *result = (PyObject*)user_data;
    PyObject *obj_var;
    obj_var = PyGccBasicBlock_New(bb);
    if (!obj_var) {
        return true;
    }

    /* It appears that with optimization there can be occasional NULLs,
       which get turned into None.  Skip them:
    */
    if (obj_var != Py_None) {
        if (-1 == PyList_Append(result, obj_var)) {
            Py_DECREF(obj_var);
            return true;
        }

        /* Success: */
    }
    Py_DECREF(obj_var);
    return false;
}

PyObject *
PyGccCfg_get_basic_blocks(PyGccCfg *self, void *closure)
{
    IMPL_LIST_MAKER(gcc_cfg_for_each_block,
                    self->cfg,
                    add_block_to_list)
}

extern PyTypeObject PyGccLabelDecl_TypeObj;

PyObject *
PyGccCfg_get_block_for_label(PyObject *s, PyObject *args)
{
    struct PyGccCfg *self = (struct PyGccCfg *)s;
    struct PyGccTree *label_decl;
    int uid;
    basic_block bb;

    if (!PyArg_ParseTuple(args,
                          "O!:get_block_for_label",
                          &PyGccLabelDecl_TypeObj, &label_decl)) {
        return NULL;
    }

    /* See also gcc/tree-cfg.c: label_to_block_fn */
    uid = LABEL_DECL_UID(label_decl->t.inner);

    if (uid < 0 ||
        (
         (
#if (GCC_VERSION >= 4008)
          vec_safe_length(self->cfg.inner->x_label_to_block_map)
#else
          VEC_length (basic_block, self->cfg.inner->x_label_to_block_map)
#endif
         )
         <=
         (unsigned int) uid)
        ) {
        return PyErr_Format(PyExc_ValueError,
                            "uid %i not found", uid);
    }

    bb = GCC_COMPAT_VEC_INDEX(basic_block,
                              self->cfg.inner->x_label_to_block_map,
                              uid);

    return PyGccBasicBlock_New(gcc_private_make_cfg_block(bb));
}

PyObject *
PyGccCfg_New(gcc_cfg cfg)
{
    struct PyGccCfg *obj;

    if (!cfg.inner) {
	Py_RETURN_NONE;
    }

    obj = PyGccWrapper_New(struct PyGccCfg, &PyGccCfg_TypeObj);
    if (!obj) {
        goto error;
    }

    obj->cfg = cfg;

    return (PyObject*)obj;
      
error:
    return NULL;
}

void
PyGcc_WrtpMarkForPyGccCfg(PyGccCfg *wrapper)
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
