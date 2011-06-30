#   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

import gcc

from PyArg_ParseTuple import check_pyargs, log
from refcounts import check_refcounts

def on_pass_execution(optpass, fun,
                      show_traces=False,
                      verify_refcounting=False,
                      *args, **kwargs):
    # Only run in one pass
    # FIXME: should we be adding our own pass for this?
    #log(optpass)
    if optpass.name == '*warn_function_return':
        if fun:
            log(fun)
            check_pyargs(fun)

            # non-SSA version of the checker:
            check_refcounts(fun, show_traces)

    # The refcount code is too buggy for now to be on by default:
    if not verify_refcounting:
        return

    if 0: # optpass.name == 'release_ssa':
        # SSA data needed:
        assert optpass.properties_required & (1<<5)
        # methods = get_all_PyMethodDef_methods()
        # log('methods: %s' % methods)
        check_refcounts(fun, show_traces)

def is_a_method_callback(decl):
    methods = get_all_PyMethodDef_methods()
    log('methods: %s' % methods)
    # FIXME
    

def get_all_PyMethodDef_methods():
    # Locate all initializers for PyMethodDef, returning a list of
    # (gcc.Declaration, gcc.Location) for the relevant callback functions
    # (the ml_meth field, and the location of the initializer)
    log('get_all_PyMethodDef_methods')

    def get_ml_meth_decl(methoddef_initializer):
         for idx2, value2 in value.elements:
             if isinstance(idx2, gcc.Declaration):
                 if idx2.name == 'ml_meth':
                     if isinstance(value2, gcc.AddrExpr):
                         log('    GOT A PyMethodDef.ml_meth initializer declaration: %s' % value2)
                         log('      value2.operand: %r' % value2.operand) # gcc.Declaration
                         log('      value2.operand: %s' % value2.operand)
                         log('      value2.operand.function: %s' % value2.operand.function)
                         return (value2.operand, value2.location)
    result = []
    vars = gcc.get_variables()
    for var in vars:
        if isinstance(var.decl, gcc.VarDecl):
            if isinstance(var.decl.type, gcc.ArrayType):
                if str(var.decl.type.type) == 'struct PyMethodDef':
                    if var.decl.initial:
                        for idx, value in var.decl.initial.elements:
                            decl = get_ml_meth_decl(value)
                            if decl:
                                result.append(decl)
    return result

def main(**kwargs):
    gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                          on_pass_execution,
                          **kwargs)
