#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"

/*
  "location_t" is the type used throughout.  Might be nice to expose this directly.

  input.h has: 
    typedef source_location location_t;

  line-map.h has:
      A logical line/column number, i.e. an "index" into a line_map:
          typedef unsigned int source_location;

*/

PyObject *
gcc_Location_repr(struct PyGccLocation * self)
{
     return PyString_FromFormat("gcc.Location(file='%s', line=%i)",
				LOCATION_FILE(self->loc),
				LOCATION_LINE(self->loc));
}

PyObject *
gcc_Location_str(struct PyGccLocation * self)
{
     return PyString_FromFormat("%s:%i",
				LOCATION_FILE(self->loc),
				LOCATION_LINE(self->loc));
}

PyObject *
gcc_python_make_wrapper_location(location_t loc)
{
    struct PyGccLocation *location_obj = NULL;
  
    location_obj = PyObject_New(struct PyGccLocation, &gcc_LocationType);
    if (!location_obj) {
        goto error;
    }

    location_obj->loc = loc;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)location_obj;
      
error:
    return NULL;
}

/*
  "struct control_flow_graph" is declared in basic-block.h, c.f.:
      struct GTY(()) control_flow_graph {
           ... snip ...
      }
*/
#include "basic-block.h"

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
  "struct function" is declared in function.h, c.f.:
      struct GTY(()) function {
           ... snip ...
      };
*/

#include "function.h"

PyObject *
gcc_Function_repr(struct PyGccFunction * self)
{
     PyObject *name = NULL;
     PyObject *result = NULL;
     tree decl;

     assert(self->fun);
     decl = self->fun->decl;
     if (DECL_NAME(decl)) {
	 name = PyString_FromString(IDENTIFIER_POINTER (DECL_NAME(decl)));
     } else {
	 name = PyString_FromString("(unnamed)");
     }

     if (!name) {
         goto error;
     }

     result = PyString_FromFormat("gcc.Function('%s')",
				  PyString_AsString(name));
     Py_DECREF(name);

     return result;
error:
     Py_XDECREF(name);
     Py_XDECREF(result);
     return NULL;
}

PyObject *
gcc_python_make_wrapper_function(struct function *fun)
{
    struct PyGccFunction *obj;

    if (!fun) {
	Py_RETURN_NONE;
    }

#if 0
    printf("gcc_python_make_wrapper_function(%p)\n", fun);
    
    printf("struct eh_status *eh: %p\n", fun->eh);
    printf("struct control_flow_graph *cfg: %p\n", fun->cfg);
    printf("struct gimple_seq_d *gimple_body: %p\n", fun->gimple_body);
    printf("struct gimple_df *gimple_df: %p\n", fun->gimple_df);
    printf("struct loops *x_current_loops: %p\n", fun->x_current_loops);
    printf("struct stack_usage *su: %p\n", fun->su);
 #if 0
    printf("htab_t GTY((skip)) value_histogram\n");
    printf("tree decl;\n");
    printf("tree static_chain_decl;\n");
    printf("tree nonlocal_goto_save_area;\n");
    printf("VEC(tree,gc) *local_decls: local_decls;\n");
    printf("struct machine_function * GTY ((maybe_undef)) machine;\n");
    printf("struct language_function * language;\n");
    printf("htab_t GTY ((param_is (union tree_node))) used_types_hash;\n");
    printf("int last_stmt_uid;\n");
    printf("int funcdef_no;\n");
    printf("location_t function_start_locus;\n");
    printf("location_t function_end_locus;\n");
    printf("unsigned int curr_properties;\n");
    printf("unsigned int last_verified;\n");
    printf("const char * GTY((skip)) cannot_be_copied_reason;\n");

    printf("unsigned int va_list_gpr_size : 8;\n");
    printf("unsigned int va_list_fpr_size : 8;\n");
    printf("unsigned int calls_setjmp : 1;\n");
    printf("unsigned int calls_alloca : 1;\n");
    printf("unsigned int has_nonlocal_label : 1;\n");
    printf("unsigned int cannot_be_copied_set : 1;\n");
    printf("unsigned int stdarg : 1;\n");
    printf("unsigned int dont_save_pending_sizes_p : 1;\n");
    printf("unsigned int after_inlining : 1;\n");
    printf("unsigned int always_inline_functions_inlined : 1;\n");
    printf("unsigned int can_throw_non_call_exceptions : 1;\n");

    printf("unsigned int returns_struct : 1;\n");
    printf("unsigned int returns_pcc_struct : 1;\n");
    printf("unsigned int after_tree_profile : 1;\n");
    printf("unsigned int has_local_explicit_reg_vars : 1;\n");
    printf("unsigned int is_thunk : 1;\n");
 #endif
#endif

    obj = PyObject_New(struct PyGccFunction, &gcc_FunctionType);
    if (!obj) {
        goto error;
    }

    obj->fun = fun;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)obj;
      
error:
    return NULL;
}

/*
    Code for various tree types
 */
PyObject *
gcc_Declaration_repr(struct PyGccTree * self)
{
     PyObject *name = NULL;
     PyObject *result = NULL;

     name = gcc_Declaration_get_name(self, NULL);
     if (!name) {
         goto error;
     }

     result = PyString_FromFormat("gcc.Declaration('%s')",
				  PyString_AsString(name));
     Py_DECREF(name);

     return result;
error:
     Py_XDECREF(name);
     Py_XDECREF(result);
     return NULL;
     
}

/* 
   GCC's debug_tree is implemented in:
     gcc/print-tree.c
   e.g. in:
     /usr/src/debug/gcc-4.6.0-20110321/gcc/print-tree.c
   and appears to be a good place to look when figuring out how the tree data
   works.

   FIXME: do we want a unique PyGccTree per tree address? (e.g. by maintaining a dict?)
   (what about lifetimes?)
*/
PyObject *
gcc_python_make_wrapper_tree(tree t)
{
    struct PyGccTree *tree_obj = NULL;
    PyTypeObject* tp;
  
    tp = gcc_python_autogenerated_tree_type_for_tree(t);
    assert(tp);
    printf("tp:%p\n", tp);
    
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
  PEP-7  
Local variables:
c-basic-offset: 4
End:
*/
