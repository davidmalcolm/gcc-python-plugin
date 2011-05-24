#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"

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
     const char *name = NULL;
     PyObject *result = NULL;
     tree decl;

     assert(self->fun);
     decl = self->fun->decl;
     if (DECL_NAME(decl)) {
         name = IDENTIFIER_POINTER (DECL_NAME(decl));
     } else {
         name = "(unnamed)";
     }

     if (!name) {
         goto error;
     }

     result = gcc_python_string_from_format("gcc.Function('%s')",
                                            name);
     return result;
error:
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
    printf("tree decl: %p;\n", fun->decl);
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
  PEP-7  
Local variables:
c-basic-offset: 4
End:
*/
