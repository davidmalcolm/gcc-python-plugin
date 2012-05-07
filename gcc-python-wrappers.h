/*
   Copyright 2011, 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011, 2012 Red Hat, Inc.

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
gcc_python_register_attribute(PyObject *self, PyObject *args, PyObject *kwargs);

/* gcc-python-callbacks.c: */
int gcc_python_is_within_event(enum plugin_event *out_event);

PyObject*
gcc_python_register_callback(PyObject *self, PyObject *args, PyObject *kwargs);

/* gcc-python-callgraph.c: */
PyObject *
gcc_CallgraphEdge_repr(struct PyGccCallgraphEdge * self);

PyObject *
gcc_CallgraphEdge_str(struct PyGccCallgraphEdge * self);

PyObject *
gcc_CallgraphNode_repr(struct PyGccCallgraphNode * self);

PyObject *
gcc_CallgraphNode_str(struct PyGccCallgraphNode * self);

extern PyObject *
gcc_CallgraphNode_get_callers(struct PyGccCallgraphNode * self);

extern PyObject *
gcc_CallgraphNode_get_callees(struct PyGccCallgraphNode * self);

PyObject *
gcc_python_get_callgraph_nodes(PyObject *self, PyObject *args);

/* gcc-python-diagnostics.c: */
PyObject*
gcc_python_permerror(PyObject *self, PyObject *args);

PyObject *
gcc_python_error(PyObject *self, PyObject *args, PyObject *kwargs);

PyObject *
gcc_python_warning(PyObject *self, PyObject *args, PyObject *kwargs);

PyObject *
gcc_python_inform(PyObject *self, PyObject *args, PyObject *kwargs);

/* gcc-python-pass.c: */
extern PyObject *
gcc_python_make_wrapper_pass(struct opt_pass *pass);

/* gcc-python-location.c: */
PyObject *
gcc_Location_repr(struct PyGccLocation * self);

PyObject *
gcc_Location_str(struct PyGccLocation * self);

PyObject *
gcc_Location_richcompare(PyObject *o1, PyObject *o2, int op);

/* gcc-python-cfg.c: */
PyObject *
gcc_BasicBlock_get_preds(PyGccBasicBlock *self, void *closure);

PyObject *
gcc_BasicBlock_get_succs(PyGccBasicBlock *self, void *closure);

PyObject *
gcc_BasicBlock_get_gimple(PyGccBasicBlock *self, void *closure);

PyObject *
gcc_BasicBlock_get_phi_nodes(PyGccBasicBlock *self, void *closure);

PyObject *
gcc_BasicBlock_get_rtl(PyGccBasicBlock *self, void *closure);

PyObject *
gcc_Cfg_get_basic_blocks(PyGccCfg *self, void *closure);

PyObject *
gcc_Cfg_get_block_for_label(PyObject *self, PyObject *args);

/* autogenerated-tree.c: */

/* return -1 if there isn't an enum tree_code associated with this type */
int
gcc_python_tree_type_object_as_tree_code(PyObject *cls,
                                         enum tree_code *out);

/* gcc-python-tree.c: */
PyObject *
gcc_Tree_str(struct PyGccTree * self);

long
gcc_Tree_hash(struct PyGccTree * self);

PyObject *
gcc_Tree_richcompare(PyObject *o1, PyObject *o2, int op);

PyObject *
gcc_Tree_get_str_no_uid(struct PyGccTree *self, void *closure);

PyObject *
gcc_Tree_get_symbol(PyObject *cls, PyObject *args);

PyObject *
gcc_Function_repr(struct PyGccFunction * self);

PyObject *
gcc_Declaration_get_name(struct PyGccTree *self, void *closure);

PyObject *
gcc_Declaration_repr(struct PyGccTree * self);

PyObject *
gcc_FunctionDecl_get_fullname(struct PyGccTree *self, void *closure);

PyObject *
gcc_IdentifierNode_repr(struct PyGccTree * self);

PyObject *
gcc_Type_get_attributes(struct PyGccTree *self, void *closure);

PyObject *
gcc_Type_get_sizeof(struct PyGccTree *self, void *closure);

PyObject *
gcc_FunctionType_get_argument_types(struct PyGccTree * self,void *closure);

PyObject *
gcc_Constructor_get_elements(PyObject *self, void *closure);

PyObject *
gcc_IntegerConstant_get_constant(struct PyGccTree * self, void *closure);

PyObject *
gcc_IntegerConstant_repr(struct PyGccTree * self);

PyObject *
gcc_RealCst_get_constant(struct PyGccTree * self, void *closure);

PyObject *
gcc_RealCst_repr(struct PyGccTree * self);

PyObject *
gcc_MethodType_get_argument_types(struct PyGccTree * self,void *closure);

PyObject *
gcc_StringConstant_repr(struct PyGccTree * self);

PyObject *
gcc_TypeDecl_get_pointer(struct PyGccTree *self, void *closure);

PyObject *
gcc_TreeList_repr(struct PyGccTree * self);

PyObject *
gcc_NamespaceDecl_lookup(struct PyGccTree * self, PyObject *args, PyObject *kwargs);

/* gcc-python-gimple.c: */
PyObject *
gcc_Gimple_repr(struct PyGccGimple * self);

PyObject *
gcc_Gimple_str(struct PyGccGimple * self);

PyObject *
gcc_Gimple_walk_tree(struct PyGccGimple * self, PyObject *args, PyObject *kwargs);

PyObject *
gcc_Gimple_get_rhs(struct PyGccGimple *self, void *closure);

PyObject *
gcc_Gimple_get_str_no_uid(struct PyGccGimple *self, void *closure);

PyObject *
gcc_GimpleCall_get_args(struct PyGccGimple *self, void *closure);

PyObject *
gcc_GimplePhi_get_args(struct PyGccGimple *self, void *closure);

PyObject *
gcc_GimpleSwitch_get_labels(struct PyGccGimple *self, void *closure);

/* gcc-python-option.c: */
int gcc_python_option_is_enabled(enum opt_code opt_code);

const struct cl_option*
gcc_python_option_to_cl_option(PyGccOption * self);

int
gcc_Option_init(PyGccOption * self, PyObject *args, PyObject *kwargs);

PyObject *
gcc_Option_repr(PyGccOption * self);

PyObject *
gcc_Option_is_enabled(PyGccOption * self, void *closure);

/* gcc-python-pass.c: */
int
gcc_GimplePass_init(PyObject *self, PyObject *args, PyObject *kwds);

int
gcc_RtlPass_init(PyObject *self, PyObject *args, PyObject *kwds);

int
gcc_SimpleIpaPass_init(PyObject *self, PyObject *args, PyObject *kwds);

int
gcc_IpaPass_init(PyObject *self, PyObject *args, PyObject *kwds);

PyObject *
gcc_Pass_repr(struct PyGccPass * self);

PyObject *
gcc_Pass_get_dump_enabled(struct PyGccPass *self, void *closure);

int
gcc_Pass_set_dump_enabled(struct PyGccPass *self, PyObject *value, void *closure);

PyObject *
gcc_Pass_get_roots(PyObject *cls, PyObject *noargs);

PyObject *
gcc_Pass_get_by_name(PyObject *cls, PyObject *args, PyObject *kwargs);

PyObject *
gcc_Pass_register_before(struct PyGccPass *self, PyObject *args, PyObject *kwargs);

PyObject *
gcc_Pass_register_after(struct PyGccPass *self, PyObject *args, PyObject *kwargs);

PyObject *
gcc_Pass_replace(struct PyGccPass *self, PyObject *args, PyObject *kwargs);


/* gcc-python-pretty-printer.c: */
#include "pretty-print.h"
struct PyGccPrettyPrinter {
    PyObject_HEAD
    pretty_printer pp;
    FILE *file_ptr;
    char buf[1024]; /* FIXME */
};

extern PyTypeObject gcc_PrettyPrinterType;

PyObject*
gcc_python_pretty_printer_new(void);

pretty_printer*
gcc_python_pretty_printer_as_pp(PyObject *obj);

PyObject*
gcc_python_pretty_printer_as_string(PyObject *obj);

void
gcc_PrettyPrinter_dealloc(PyObject *obj);

/* gcc-python-rtl.c: */
PyObject *
gcc_Rtl_get_location(struct PyGccRtl *self, void *closure);

PyObject *
gcc_Rtl_get_operands(struct PyGccRtl *self, void *closure);

PyObject *
gcc_Rtl_repr(struct PyGccRtl * self);

PyObject *
gcc_Rtl_str(struct PyGccRtl * self);

PyObject *
gcc_tree_list_from_chain(tree t);

PyObject *
gcc_python_tree_make_list_from_tree_list_chain(tree t);

PyObject *
gcc_python_tree_make_list_of_pairs_from_tree_list_chain(tree t);

/* gcc-python-version.c: */
void
gcc_python_version_init(struct plugin_gcc_version *version);

PyObject *
gcc_python_get_plugin_gcc_version(PyObject *self, PyObject *args);

PyObject *
gcc_python_get_gcc_version(PyObject *self, PyObject *args);

/* gcc-python-wrappers.c: */
void
gcc_python_wrapper_init(void);

PyObject *
gcc_python__force_garbage_collection(PyObject *self, PyObject *args);

PyObject *
gcc_python__gc_selftest(PyObject *self, PyObject *args);

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/

#endif /* INCLUDED__WRAPPERS_H */
