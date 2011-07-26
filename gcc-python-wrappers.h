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

#ifndef INCLUDED__WRAPPERS_H
#define INCLUDED__WRAPPERS_H

#include "gcc-python.h"
#include "tree-pass.h"
#include "opts.h"

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
gcc_BasicBlock_get_phi_nodes(PyGccBasicBlock *self, void *closure);

PyObject *
gcc_Cfg_get_basic_blocks(PyGccCfg *self, void *closure);

PyObject *
gcc_Tree_str(struct PyGccTree * self);

long
gcc_Tree_hash(struct PyGccTree * self);

PyObject *
gcc_Tree_richcompare(PyObject *o1, PyObject *o2, int op);

PyObject *
gcc_Tree_get_str_no_uid(struct PyGccTree *self, void *closure);

PyObject *
gcc_Function_repr(struct PyGccFunction * self);

PyObject *
gcc_Declaration_get_name(struct PyGccTree *self, void *closure);

PyObject *
gcc_Declaration_repr(struct PyGccTree * self);

PyObject *
gcc_FunctionType_get_argument_types(struct PyGccTree * self,void *closure);

PyObject *
gcc_Constructor_get_elements(PyObject *self, void *closure);

PyObject *
gcc_IntegerConstant_get_constant(struct PyGccTree * self, void *closure);

PyObject *
gcc_TypeDecl_get_pointer(struct PyGccTree *self, void *closure);

PyObject *
gcc_Gimple_repr(struct PyGccGimple * self);

PyObject *
gcc_Gimple_str(struct PyGccGimple * self);

PyObject *
gcc_Gimple_get_rhs(struct PyGccGimple *self, void *closure);

PyObject *
gcc_Gimple_get_str_no_uid(struct PyGccGimple *self, void *closure);

PyObject *
gcc_GimpleCall_get_args(struct PyGccGimple *self, void *closure);

PyObject *
gcc_GimplePhi_get_args(struct PyGccGimple *self, void *closure);

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
PyObject *
gcc_Pass_repr(struct PyGccPass * self);

PyObject *
gcc_Pass_get_roots(PyObject *cls, PyObject *noargs);

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

PyObject *
gcc_tree_list_from_chain(tree t);

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/

#endif /* INCLUDED__WRAPPERS_H */
