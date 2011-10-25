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
from libcpychecker.formatstrings import check_pyargs
from libcpychecker.utils import log
from libcpychecker.refcounts import check_refcounts, get_traces
from libcpychecker.attributes import register_our_attributes

class CpyChecker(gcc.GimplePass):
    """
    The custom pass that implements our extra compile-time checks
    """
    def __init__(self,
                 dump_traces=False,
                 show_traces=False,
                 verify_pyargs=True,
                 verify_refcounting=False,
                 show_possible_null_derefs=False):
        gcc.GimplePass.__init__(self, 'cpychecker')
        self.dump_traces = dump_traces
        self.show_traces = show_traces
        self.verify_pyargs = verify_pyargs
        self.verify_refcounting = verify_refcounting
        self.show_possible_null_derefs = show_possible_null_derefs

    def execute(self, fun):
        if fun:
            log('%s', fun)
            if self.verify_pyargs:
                check_pyargs(fun)

            # The refcount code is too buggy for now to be on by default:
            if self.verify_refcounting:
                check_refcounts(fun, self.dump_traces, self.show_traces,
                                self.show_possible_null_derefs)

def is_a_method_callback(decl):
    methods = get_all_PyMethodDef_methods()
    log('methods: %s', methods)
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
                         log('    GOT A PyMethodDef.ml_meth initializer declaration: %s', value2)
                         log('      value2.operand: %r', value2.operand) # gcc.Declaration
                         log('      value2.operand: %s', value2.operand)
                         log('      value2.operand.function: %s', value2.operand.function)
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
    # Register our custom attributes:
    gcc.register_callback(gcc.PLUGIN_ATTRIBUTES,
                          register_our_attributes)

    # Register our GCC pass:
    ps = CpyChecker(**kwargs)

    if 1:
        # non-SSA version:
        ps.register_before('*warn_function_return')
    else:
        # SSA version:
        ps.register_after('ssa')
