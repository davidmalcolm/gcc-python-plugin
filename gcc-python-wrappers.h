#ifndef INCLUDED__WRAPPERS_H
#define INCLUDED__WRAPPERS_H

#include "tree-pass.h"

PyMODINIT_FUNC initoptpass(void);

extern PyObject *
gcc_python_make_wrapper_opt_pass(struct opt_pass *ptr);

PyObject *
gcc_Location_repr(struct PyGccLocation * self);

PyObject *
gcc_Location_str(struct PyGccLocation * self);

PyObject *
gcc_BasicBlock_get_preds(PyGccBasicBlock *self, void *closure);

PyObject *
gcc_BasicBlock_get_succs(PyGccBasicBlock *self, void *closure);

PyObject *
gcc_BasicBlock_get_gimple(PyGccBasicBlock *self, void *closure);

PyObject *
gcc_Cfg_get_basic_blocks(PyGccCfg *self, void *closure);

PyObject *
gcc_Function_repr(struct PyGccFunction * self);

PyObject *
gcc_Declaration_get_name(struct PyGccTree *self, void *closure);

PyObject *
gcc_Declaration_repr(struct PyGccTree * self);

#endif /* INCLUDED__WRAPPERS_H */
