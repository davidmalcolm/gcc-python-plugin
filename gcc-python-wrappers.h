#ifndef INCLUDED__WRAPPERS_H
#define INCLUDED__WRAPPERS_H

#include "gcc-python.h"
#include "tree-pass.h"

PyMODINIT_FUNC initoptpass(void);

extern PyObject *
gcc_python_make_wrapper_pass(struct opt_pass *pass);

PyObject *
gcc_Location_repr(struct PyGccLocation * self);

PyObject *
gcc_Location_str(struct PyGccLocation * self);

PyObject *
gcc_Location_richcompare(PyObject *o1, PyObject *o2, int op);

PyObject *
gcc_BasicBlock_get_preds(PyGccBasicBlock *self, void *closure);

PyObject *
gcc_BasicBlock_get_succs(PyGccBasicBlock *self, void *closure);

PyObject *
gcc_BasicBlock_get_gimple(PyGccBasicBlock *self, void *closure);

PyObject *
gcc_Cfg_get_basic_blocks(PyGccCfg *self, void *closure);

PyObject *
gcc_Tree_str(struct PyGccTree * self);

PyObject *
gcc_Tree_richcompare(PyObject *o1, PyObject *o2, int op);

PyObject *
gcc_Function_repr(struct PyGccFunction * self);

PyObject *
gcc_Declaration_get_name(struct PyGccTree *self, void *closure);

PyObject *
gcc_Declaration_repr(struct PyGccTree * self);

PyObject *
gcc_Constructor_get_elements(PyObject *self, void *closure);

PyObject *
gcc_Gimple_repr(struct PyGccGimple * self);

PyObject *
gcc_Gimple_str(struct PyGccGimple * self);

PyObject *
gcc_Gimple_get_rhs(struct PyGccGimple *self, void *closure);

PyObject *
gcc_GimpleCall_get_args(struct PyGccGimple *self, void *closure);

PyObject *
gcc_Pass_repr(struct PyGccPass * self);

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

PyObject *
gcc_tree_list_from_chain(tree t);

#endif /* INCLUDED__WRAPPERS_H */
