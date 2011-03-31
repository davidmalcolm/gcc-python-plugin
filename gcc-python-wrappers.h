#ifndef INCLUDED__WRAPPERS_H
#define INCLUDED__WRAPPERS_H

#include "tree-pass.h"

PyMODINIT_FUNC initoptpass(void);

extern PyObject *
gcc_python_make_wrapper_opt_pass(struct opt_pass *ptr);

#endif /* INCLUDED__WRAPPERS_H */
