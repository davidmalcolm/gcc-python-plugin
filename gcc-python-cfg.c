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

#include "basic-block.h"
#include "rtl.h"

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
gcc_python_make_wrapper_edge(edge e)
{
    struct PyGccEdge *obj;

    if (!e) {
	Py_RETURN_NONE;
    }

    obj = PyObject_New(struct PyGccEdge, &gcc_EdgeType);
    if (!obj) {
        goto error;
    }

    obj->e = e;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)obj;
      
error:
    return NULL;
}

/*
  "struct basic_block_def" is declared in basic-block.h, c.f:
      struct GTY((chain_next ("%h.next_bb"), chain_prev ("%h.prev_bb"))) basic_block_def {
           ... snip ...
      }
  and there are these typedefs to pointers defined in coretypes.h:
      typedef struct basic_block_def *basic_block;
      typedef const struct basic_block_def *const_basic_block;
 */
PyObject *    
VEC_edge_as_PyList(VEC(edge,gc) *vec_edges)
{
    PyObject *result = NULL;
    int i;
    edge e;
    
    result = PyList_New(VEC_length(edge, vec_edges));
    if (!result) {
	goto error;
    }

    FOR_EACH_VEC_ELT(edge, vec_edges, i, e) {
	PyObject *item;
	item = gcc_python_make_wrapper_edge(e);
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


PyObject *
gcc_BasicBlock_get_preds(PyGccBasicBlock *self, void *closure)
{
    return VEC_edge_as_PyList(self->bb->preds);
}

PyObject *
gcc_BasicBlock_get_succs(PyGccBasicBlock *self, void *closure)
{
    return VEC_edge_as_PyList(self->bb->succs);
}

static PyObject *
gcc_python_gimple_seq_to_list(gimple_seq seq)
{
    gimple_stmt_iterator gsi;
    PyObject *result = NULL;

    result = PyList_New(0);
    if (!result) {
	goto error;
    }

    for (gsi = gsi_start (seq);
	 !gsi_end_p (gsi);
	 gsi_next (&gsi)) {

	gimple stmt = gsi_stmt(gsi);
	PyObject *obj_stmt;

	obj_stmt = gcc_python_make_wrapper_gimple(stmt);
	if (!obj_stmt) {
	    goto error;
	}

	if (PyList_Append(result, obj_stmt)) {
	    goto error;
	}

#if 0
	printf("  gimple: %p code: %s (%i) %s:%i num_ops=%i\n", 
	       stmt,
	       gimple_code_name[gimple_code(stmt)],
	       gimple_code(stmt),
	       gimple_filename(stmt),
	       gimple_lineno(stmt),
	       gimple_num_ops(stmt));
#endif
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;    
}


PyObject *
gcc_BasicBlock_get_gimple(PyGccBasicBlock *self, void *closure)
{
    assert(self);
    assert(self->bb);

    if (self->bb->flags & BB_RTL) {
	Py_RETURN_NONE;
    }

    if (NULL == self->bb->il.gimple) {
	Py_RETURN_NONE;
    }

    return gcc_python_gimple_seq_to_list(self->bb->il.gimple->seq);
}

PyObject *
gcc_BasicBlock_get_phi_nodes(PyGccBasicBlock *self, void *closure)
{
    assert(self);
    assert(self->bb);

    if (self->bb->flags & BB_RTL) {
	Py_RETURN_NONE;
    }

    if (NULL == self->bb->il.gimple) {
	Py_RETURN_NONE;
    }

    return gcc_python_gimple_seq_to_list(self->bb->il.gimple->phi_nodes);
}

PyObject *
gcc_BasicBlock_get_rtl(PyGccBasicBlock *self, void *closure)
{
    PyObject *result = NULL;

    rtx insn;

    if (!(self->bb->flags & BB_RTL)) {
	Py_RETURN_NONE;
    }

#if 0
    /* Debugging help: */
    {
        fprintf(stderr, "--BEGIN--\n");
        FOR_BB_INSNS(self->bb, insn) {
            print_rtl_single (stderr, insn);
        }
        fprintf(stderr, "-- END --\n");
    }
#endif

    result = PyList_New(0);
    if (!result) {
	goto error;
    }

    FOR_BB_INSNS(self->bb, insn) {
	PyObject *obj;

	obj = gcc_python_make_wrapper_rtl(insn);
	if (!obj) {
	    goto error;
	}

	if (PyList_Append(result, obj)) {
	    goto error;
	}
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
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
    basic_block bb = (basic_block)ptr;
    struct PyGccBasicBlock *obj;

    if (!bb) {
	Py_RETURN_NONE;
    }

    obj = PyObject_New(struct PyGccBasicBlock, &gcc_BasicBlockType);
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
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)obj;
      
error:
    return NULL;
}

static PyObject *basic_block_wrapper_cache = NULL;
PyObject *
gcc_python_make_wrapper_basic_block(basic_block bb)
{
    return gcc_python_lazily_create_wrapper(&basic_block_wrapper_cache,
					    bb,
					    real_make_basic_block_wrapper);
}

/*
  "struct control_flow_graph" is declared in basic-block.h, c.f.:
      struct GTY(()) control_flow_graph {
           ... snip ...
      }
*/
PyObject *
gcc_Cfg_get_basic_blocks(PyGccCfg *self, void *closure)
{
    PyObject *result = NULL;
    int i;
    
    result = PyList_New(self->cfg->x_n_basic_blocks);
    if (!result) {
	goto error;
    }

    for (i = 0; i < self->cfg->x_n_basic_blocks; i++) {
	PyObject *item;
	item = gcc_python_make_wrapper_basic_block(VEC_index(basic_block, self->cfg->x_basic_block_info, i));
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
        (VEC_length (basic_block, self->cfg->x_label_to_block_map)
         <=
         (unsigned int) uid)
        ) {
        return PyErr_Format(PyExc_ValueError,
                            "uid %i not found", uid);
    }

    bb = VEC_index(basic_block, self->cfg->x_label_to_block_map, uid);

    return gcc_python_make_wrapper_basic_block(bb);
}

PyObject *
gcc_python_make_wrapper_cfg(struct control_flow_graph *cfg)
{
    struct PyGccCfg *obj;

    if (!cfg) {
	Py_RETURN_NONE;
    }

    obj = PyObject_New(struct PyGccCfg, &gcc_CfgType);
    if (!obj) {
        goto error;
    }

    obj->cfg = cfg;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)obj;
      
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
