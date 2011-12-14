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

# Verification of data initializers (e.g. PyMethodDef tables)

import gcc

from gccutils import check_isinstance

from libcpychecker.utils import log

def check_initializers():
    # Invoked by the "cpychecker-ipa" pass, once per compilation unit
    verify_any_PyMethodDef_flags()

from collections import OrderedDict
class StructInitializer(object):
    def __init__(self, ctor):
        check_isinstance(ctor, gcc.Constructor)
        self.ctor = ctor

        # Mapping from string fieldname to gcc.Tree value:
        self.fielddict = OrderedDict()
        for key, tree in ctor.elements:
            check_isinstance(key, gcc.FieldDecl)
            self.fielddict[key.name] = tree

    def __repr__(self):
        attrs = ','.join(['%s=%s' % (k, v)
                          for k, v in self.fielddict.items()])
        return '%s(%s)' % (self.__class__.__name__, attrs)

    def int_field(self, fieldname):
        """
        Extract the initializer for the given field, as an int
        """
        tree = self.fielddict[fieldname]
        check_isinstance(tree, gcc.IntegerCst)
        return tree.constant

    def char_ptr_field(self, fieldname):
        tree = self.fielddict[fieldname]
        if isinstance(tree, gcc.IntegerCst):
            if tree.constant == 0:
                return None # NULL
        # go past casts:
        if isinstance(tree, gcc.NopExpr):
            tree = tree.operand
        check_isinstance(tree, gcc.AddrExpr)
        check_isinstance(tree.operand, gcc.StringCst)
        return tree.operand.constant

    def function_ptr_field(self, fieldname):
        """
        Extract the initializer for the given field, as a gcc.FunctionDecl,
        or None for NULL.
        """
        tree = self.fielddict[fieldname]

        # go past casts:
        if isinstance(tree, gcc.NopExpr):
            tree = tree.operand
        if isinstance(tree, gcc.IntegerCst):
            if tree.constant == 0:
                return None # NULL
        check_isinstance(tree, gcc.AddrExpr)
        return tree.operand

class PyMethodDefInitializer(StructInitializer):
    def get_location(self):
        return self.fielddict['ml_meth'].location

# Adapted from Include/methodobject.h:
METH_OLDARGS  = 0x0000
METH_VARARGS  = 0x0001
METH_KEYWORDS = 0x0002
METH_NOARGS   = 0x0004
METH_O        = 0x0008
METH_CLASS    = 0x0010
METH_STATIC   = 0x0020
METH_COEXIST  = 0x0040

def verify_any_PyMethodDef_flags():
    """
    Check all initializers for PyMethodDef arrays.
    Verify that the flags used match the real signature of the callback
    function (albeit usually cast to a PyCFunction):
      http://docs.python.org/c-api/structures.html#PyMethodDef
    """
    methods = get_all_PyMethodDef_initializers()
    #from pprint import pprint
    #pprint(methods)

    for si in methods:
        if 0:
            print(si)
        ml_meth = si.function_ptr_field('ml_meth')
        ml_flags = si.int_field('ml_flags')
        if 0:
            print('  ml_meth: %r' % ml_meth)
            print('  ml_flags: %r' % ml_flags)
        check_isinstance(ml_flags, int)

        if ml_meth is not None:
            check_isinstance(ml_meth, gcc.FunctionDecl)
            if ml_flags & METH_KEYWORDS:
                expargs = 3
                exptypemsg = 'expected ml_meth callback of type "PyObject (fn)(someobject *, PyObject *args, PyObject *kwargs)" due to METH_KEYWORDS flag'
            else:
                expargs = 2
                exptypemsg = 'expected ml_meth callback of type "PyObject (fn)(someobject *, PyObject *)"'
            actualargs = len(ml_meth.type.argument_types)
            if expargs != actualargs:
                gcc.error(si.get_location(),
                          'flags do not match callback signature for %r'
                          ' within PyMethodDef table'
                          % ml_meth.name)
                gcc.inform(si.get_location(),
                           exptypemsg + ' (%s arguments)' % expargs)
                gcc.inform(si.get_location(),
                           'actual type of underlying callback: %s' % ml_meth.type
                            + ' (%s arguments)' % actualargs)
                gcc.inform(si.get_location(),
                           'see http://docs.python.org/c-api/structures.html#PyMethodDef')

def get_all_PyMethodDef_initializers():
    """
    Locate all initializers for PyMethodDef, returning a list
    of StructInitializer instances
    """
    log('get_all_PyMethodDef_initializers')

    result = []
    vars = gcc.get_variables()
    for var in vars:
        if isinstance(var.decl, gcc.VarDecl):
            if isinstance(var.decl.type, gcc.ArrayType):
                if str(var.decl.type.type) == 'struct PyMethodDef':
                    if var.decl.initial:
                        table = []
                        for idx, ctor in var.decl.initial.elements:
                            #print idx, ctor
                            si = PyMethodDefInitializer(ctor)
                            table.append(si)
                        # Warn about missing sentinel entry with
                        #   ml->ml_name == NULL
                        ml_name = table[-1].char_ptr_field('ml_name')
                        if 0:
                            print('final ml_name: %r' % ml_name)
                        if ml_name is not None:
                            gcc.error(table[-1].get_location(),
                                      'missing NULL sentinel value at end of PyMethodDef table')
                        result += table
    return result

class PyTypeObjectInitializer(StructInitializer):
    pass

def get_all_PyTypeObject_initializers():
    """
    Locate all initializers for PyTypeObject, returning a list
    of PyTypeObjectInitializer instances
    """
    log('get_all_PyTypeObject_initializers')

    result = []
    vars = gcc.get_variables()
    for var in vars:
        if isinstance(var.decl, gcc.VarDecl):
            if str(var.decl.type) == 'struct PyTypeObject':
                ctor = var.decl.initial
                if ctor:
                    si = PyTypeObjectInitializer(ctor)
                    result.append(si)
    return result
