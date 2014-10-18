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

#ifndef INCLUDED__WRAPPERS_H
#define INCLUDED__WRAPPERS_H

#include "gcc-python.h"
#include "tree-pass.h"
#include "opts.h"
#include "cgraph.h"

/*
  Create a callback for use in a gcc for_each iterator to make wrapper
  objects for the underlying gcc objects being iterated, and append the
  wrapper objects to a Python list
*/
#define IMPL_APPENDER(FNNAME, KIND, MAKE_WRAPPER) \
  static bool FNNAME(KIND var, void *user_data)    \
  {                                                \
      PyObject *result = (PyObject*)user_data;     \
      PyObject *obj_var;                           \
      obj_var = MAKE_WRAPPER(var);                 \
      if (!obj_var) {                              \
          return true;                             \
      }                                            \
      if (-1 == PyList_Append(result, obj_var)) {  \
          Py_DECREF(obj_var);                      \
          return true;                             \
      }                                            \
      /* Success: */                               \
      Py_DECREF(obj_var);                          \
      return false;                                \
  }

/*
  Create the body of a function that builds a list by calling a for_each
  ITERATOR, passing in the APPENDER callback to convert the iterated items
  into Python wrapper objects
 */
#define IMPL_LIST_MAKER(ITERATOR, ARG, APPENDER) \
    PyObject *result;                            \
    result = PyList_New(0);                      \
    if (!result) {                               \
        return NULL;                             \
    }                                            \
    if (ITERATOR((ARG), APPENDER, result)) {     \
        Py_DECREF(result);                       \
        return NULL;                             \
    }                                            \
    return result;

/*
As per IMPL_LIST_MAKER, but for a global iterator that takes no ARG
 */
#define IMPL_GLOBAL_LIST_MAKER(ITERATOR, APPENDER) \
    PyObject *result;                 \
    result = PyList_New(0);           \
    if (!result) {                    \
        return NULL;                  \
    }                                 \
    if (ITERATOR(APPENDER, result)) { \
        Py_DECREF(result);            \
        return NULL;                  \
    }                                 \
    return result;

PyMODINIT_FUNC initoptpass(void);

/* gcc-python-attribute.c: */
PyObject*
PyGcc_RegisterAttribute(PyObject *self, PyObject *args, PyObject *kwargs);

/* gcc-python-callbacks.c: */
int PyGcc_IsWithinEvent(enum plugin_event *out_event);

PyObject*
PyGcc_RegisterCallback(PyObject *self, PyObject *args, PyObject *kwargs);

/* gcc-python-callgraph.c: */
PyObject *
PyGccCallgraphEdge_repr(struct PyGccCallgraphEdge * self);

PyObject *
PyGccCallgraphEdge_str(struct PyGccCallgraphEdge * self);

PyObject *
PyGccCallgraphNode_repr(struct PyGccCallgraphNode * self);

PyObject *
PyGccCallgraphNode_str(struct PyGccCallgraphNode * self);

extern PyObject *
PyGccCallgraphNode_get_callers(struct PyGccCallgraphNode * self);

extern PyObject *
PyGccCallgraphNode_get_callees(struct PyGccCallgraphNode * self);

PyObject *
PyGcc_get_callgraph_nodes(PyObject *self, PyObject *args);

/* gcc-python-diagnostics.c: */
PyObject*
PyGcc_permerror(PyObject *self, PyObject *args);

PyObject *
PyGcc_error(PyObject *self, PyObject *args, PyObject *kwargs);

PyObject *
PyGcc_warning(PyObject *self, PyObject *args, PyObject *kwargs);

PyObject *
PyGcc_inform(PyObject *self, PyObject *args, PyObject *kwargs);

/* gcc-python-pass.c: */
extern PyObject *
PyGccPass_New(struct opt_pass *pass);

/* gcc-python-location.c: */
PyObject *
PyGccLocation_repr(struct PyGccLocation * self);

PyObject *
PyGccLocation_str(struct PyGccLocation * self);

PyObject *
PyGccLocation_richcompare(PyObject *o1, PyObject *o2, int op);

long
PyGccLocation_hash(struct PyGccLocation * self);

/* gcc-python-cfg.c: */
PyObject *
PyGccBasicBlock_repr(struct PyGccBasicBlock * self);

PyObject *
PyGccBasicBlock_get_preds(PyGccBasicBlock *self, void *closure);

PyObject *
PyGccBasicBlock_get_succs(PyGccBasicBlock *self, void *closure);

PyObject *
PyGccBasicBlock_get_gimple(PyGccBasicBlock *self, void *closure);

PyObject *
PyGccBasicBlock_get_phi_nodes(PyGccBasicBlock *self, void *closure);

PyObject *
PyGccBasicBlock_get_rtl(PyGccBasicBlock *self, void *closure);

PyObject *
PyGccCfg_get_basic_blocks(PyGccCfg *self, void *closure);

PyObject *
PyGccCfg_get_block_for_label(PyObject *self, PyObject *args);

/* autogenerated-tree.c: */

/* return -1 if there isn't an enum tree_code associated with this type */
int
PyGcc_tree_type_object_as_tree_code(PyObject *cls,
                                         enum tree_code *out);

/* gcc-python-tree.c: */
/* FIXME: autogenerate these: */
extern gcc_decl
PyGccTree_as_gcc_decl(struct PyGccTree * self);

extern gcc_type
PyGccTree_as_gcc_type(struct PyGccTree * self);

extern gcc_fixed_point_type
PyGccTree_as_gcc_fixed_point_type(struct PyGccTree * self);

extern gcc_integer_type
PyGccTree_as_gcc_integer_type(struct PyGccTree * self);

extern gcc_real_type
PyGccTree_as_gcc_real_type(struct PyGccTree * self);

extern gcc_translation_unit_decl
PyGccTree_as_gcc_translation_unit_decl(struct PyGccTree * self);

extern gcc_ssa_name
PyGccTree_as_gcc_ssa_name(struct PyGccTree * self);

extern gcc_case_label_expr
PyGccTree_as_gcc_case_label_expr(struct PyGccTree * self);

extern PyObject *
PyGccBlock_New(gcc_block t);

extern PyObject *
PyGccPointerType_New(gcc_pointer_type t);

PyObject *
PyGccPointerType_repr(struct PyGccTree * self);

extern PyObject *
PyGccCaseLabelExpr_New(gcc_case_label_expr t);

PyObject *
PyGccTree_str(struct PyGccTree * self);

long
PyGccTree_hash(struct PyGccTree * self);

PyObject *
PyGccTree_richcompare(PyObject *o1, PyObject *o2, int op);

PyObject *
PyGccTree_get_str_no_uid(struct PyGccTree *self, void *closure);

PyObject *
PyGccTree_get_symbol(PyObject *cls, PyObject *args);

PyObject *
PyGccFunction_repr(struct PyGccFunction * self);

long
PyGccFunction_hash(struct PyGccFunction * self);

PyObject *
PyGccFunction_richcompare(PyObject *o1, PyObject *o2, int op);

PyObject *
PyGccArrayRef_repr(PyObject *self);

PyObject *
PyGccComponentRef_repr(PyObject *self);

PyObject *
PyGccDeclaration_get_name(struct PyGccTree *self, void *closure);

PyObject *
PyGccDeclaration_repr(struct PyGccTree * self);

PyObject *
PyGccFunctionDecl_get_fullname(struct PyGccTree *self, void *closure);

PyObject *
PyGccIdentifierNode_repr(struct PyGccTree * self);

PyObject *
PyGccType_get_attributes(struct PyGccTree *self, void *closure);

PyObject *
PyGccType_get_sizeof(struct PyGccTree *self, void *closure);

PyObject *
PyGccFunction_TypeObj_get_argument_types(struct PyGccTree * self,void *closure);

PyObject *
PyGccConstructor_get_elements(PyObject *self, void *closure);

PyObject *
PyGccIntegerConstant_get_constant(struct PyGccTree * self, void *closure);

PyObject *
PyGccIntegerConstant_repr(struct PyGccTree * self);

PyObject *
PyGccRealCst_get_constant(struct PyGccTree * self, void *closure);

PyObject *
PyGccRealCst_repr(struct PyGccTree * self);

PyObject *
PyGccIntegerType_get_signed_equivalent(struct PyGccTree * self, void *closure);

PyObject *
PyGccIntegerType_get_unsigned_equivalent(struct PyGccTree * self, void *closure);

PyObject *
PyGccIntegerType_repr(struct PyGccTree * self);

PyObject *
PyGccMethodType_get_argument_types(struct PyGccTree * self,void *closure);

PyObject *
PyGccStringConstant_repr(struct PyGccTree * self);

PyObject *
PyGccTypeDecl_get_pointer(struct PyGccTree *self, void *closure);

PyObject *
PyGccTypeDecl_get_original_type(struct PyGccTree *self, void *closure);

PyObject *
PyGccSsaName_repr(struct PyGccTree * self);

PyObject *
PyGccTreeList_repr(struct PyGccTree * self);

PyObject *
PyGccCaseLabelExpr_repr(PyObject *self);

PyObject *
PyGccNamespaceDecl_lookup(struct PyGccTree * self, PyObject *args, PyObject *kwargs);

PyObject *
PyGccNamespaceDecl_unalias(struct PyGccTree * self, PyObject *args, PyObject *kwargs);

PyObject *
PyGccNamespaceDecl_declarations(tree t);

PyObject *
PyGccNamespaceDecl_namespaces(tree t);


/* gcc-python-gimple.c: */
extern gcc_gimple_asm
PyGccGimple_as_gcc_gimple_asm(struct PyGccGimple *self);

extern gcc_gimple_assign
PyGccGimple_as_gcc_gimple_assign(struct PyGccGimple *self);

extern gcc_gimple_call
PyGccGimple_as_gcc_gimple_call(struct PyGccGimple *self);

extern gcc_gimple_return
PyGccGimple_as_gcc_gimple_return(struct PyGccGimple *self);

extern gcc_gimple_cond
PyGccGimple_as_gcc_gimple_cond(struct PyGccGimple *self);

extern gcc_gimple_phi
PyGccGimple_as_gcc_gimple_phi(struct PyGccGimple *self);

extern gcc_gimple_switch
PyGccGimple_as_gcc_gimple_switch(struct PyGccGimple *self);

extern gcc_gimple_label
PyGccGimple_as_gcc_gimple_label(struct PyGccGimple *self);

PyObject *
PyGccGimple_repr(struct PyGccGimple * self);

PyObject *
PyGccGimple_str(struct PyGccGimple * self);

long
PyGccGimple_hash(struct PyGccGimple * self);

PyObject *
PyGccGimple_richcompare(PyObject *o1, PyObject *o2, int op);

PyObject *
PyGccGimple_walk_tree(struct PyGccGimple * self, PyObject *args, PyObject *kwargs);

PyObject *
PyGccGimple_get_rhs(struct PyGccGimple *self, void *closure);

PyObject *
PyGccGimple_get_str_no_uid(struct PyGccGimple *self, void *closure);

PyObject *
PyGccGimpleCall_get_args(struct PyGccGimple *self, void *closure);

PyObject *
PyGccGimpleLabel_repr(PyObject * self);

PyObject *
PyGccGimplePhi_get_args(struct PyGccGimple *self, void *closure);

PyObject *
PyGccGimpleSwitch_get_labels(struct PyGccGimple *self, void *closure);

/* gcc-python-option.c: */
int PyGcc_option_is_enabled(enum opt_code opt_code);

const struct cl_option*
PyGcc_option_to_cl_option(PyGccOption * self);

int
PyGccOption_init(PyGccOption * self, PyObject *args, PyObject *kwargs);

PyObject *
PyGccOption_repr(PyGccOption * self);

PyObject *
PyGccOption_is_enabled(PyGccOption * self, void *closure);

/* gcc-python-pass.c: */
int
PyGccGimplePass_init(PyObject *self, PyObject *args, PyObject *kwds);

int
PyGccRtlPass_init(PyObject *self, PyObject *args, PyObject *kwds);

int
PyGccSimpleIpaPass_init(PyObject *self, PyObject *args, PyObject *kwds);

int
PyGccIpaPass_init(PyObject *self, PyObject *args, PyObject *kwds);

PyObject *
PyGccPass_repr(struct PyGccPass * self);

PyObject *
PyGccPass_get_dump_enabled(struct PyGccPass *self, void *closure);

int
PyGccPass_set_dump_enabled(struct PyGccPass *self, PyObject *value, void *closure);

PyObject *
PyGccPass_get_roots(PyObject *cls, PyObject *noargs);

PyObject *
PyGccPass_get_by_name(PyObject *cls, PyObject *args, PyObject *kwargs);

PyObject *
PyGccPass_register_before(struct PyGccPass *self, PyObject *args, PyObject *kwargs);

PyObject *
PyGccPass_register_after(struct PyGccPass *self, PyObject *args, PyObject *kwargs);

PyObject *
PyGccPass_replace(struct PyGccPass *self, PyObject *args, PyObject *kwargs);


/* gcc-python-pretty-printer.c: */
#include "pretty-print.h"
struct PyGccPrettyPrinter {
    PyObject_HEAD
    pretty_printer pp;
    FILE *file_ptr;
    char buf[1024]; /* FIXME */
};

extern PyTypeObject PyGccPrettyPrinter_TypeObj;

PyObject*
PyGccPrettyPrinter_New(void);

pretty_printer*
PyGccPrettyPrinter_as_pp(PyObject *obj);

PyObject*
PyGccPrettyPrinter_as_string(PyObject *obj);

void
PyGccPrettyPrinter_dealloc(PyObject *obj);

/* gcc-python-rtl.c: */
PyObject *
PyGccRtl_get_location(struct PyGccRtl *self, void *closure);

PyObject *
PyGccRtl_get_operands(struct PyGccRtl *self, void *closure);

PyObject *
PyGccRtl_repr(struct PyGccRtl * self);

PyObject *
PyGccRtl_str(struct PyGccRtl * self);

PyObject *
PyGcc_TreeListFromChain(tree t);

PyObject *
PyGcc_TreeMakeListFromTreeList(tree t);

PyObject *
PyGcc_TreeMakeListOfPairsFromTreeListChain(tree t);

/* gcc-python-version.c: */
void
PyGcc_version_init(struct plugin_gcc_version *version);

PyObject *
PyGcc_get_plugin_gcc_version(PyObject *self, PyObject *args);

PyObject *
PyGcc_get_gcc_version(PyObject *self, PyObject *args);

/* gcc-python-wrappers.c: */
void
PyGcc_wrapper_init(void);

PyObject *
PyGcc__force_garbage_collection(PyObject *self, PyObject *args);

PyObject *
PyGcc__gc_selftest(PyObject *self, PyObject *args);

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/

#endif /* INCLUDED__WRAPPERS_H */
