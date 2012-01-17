# -*- coding: utf-8 -*-
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
from gccutils import get_global_typedef

# Verify that this function works:
from libcpychecker.refcounts import type_is_pyobjptr_subclass

def get_struct(tagname):
    for u in gcc.get_translation_units():
        for v in u.block.vars:
            if isinstance(v, gcc.TypeDecl):
                if isinstance(v.type, gcc.RecordType):
                    if isinstance(v.type.name, gcc.IdentifierNode):
                        if v.type.name.name == tagname:
                            return v.type

def check_type(t):
    print('type: %s' % t)
    print('  is PyObject* subclass?: %s\n' % type_is_pyobjptr_subclass(t))

def check_typedef(typedef):
    print('typedef: %r' % typedef)
    decl = get_global_typedef(typedef)
    ptr_type = decl.type.pointer
    print('  ptr_type: %s' % ptr_type)
    print('  is PyObject* subclass?: %s\n' % type_is_pyobjptr_subclass(ptr_type))

def check_struct(typename):
    print('typename: %r' % typename)
    struct_type = get_struct(typename)
    print('  struct_type: %s' % struct_type)
    ptr_type = struct_type.pointer
    print('  ptr_type: %s' % ptr_type)
    print('  is PyObject* subclass?: %s\n' % type_is_pyobjptr_subclass(ptr_type))

def on_pass_execution(p, fn):
    if p.name == '*free_lang_data':
        # The '*free_lang_data' pass is called once, rather than per-function,
        # and occurs immediately after "*build_cgraph_edges", which is the
        # pass that initially builds the callgraph
        #
        # So at this point we're likely to get a good view of the types:
        check_type(gcc.Type.int())
        check_type(gcc.Type.char().pointer)
        check_typedef('PyObject')
        check_typedef('PyTypeObject')
        check_struct('FooObject')
        check_struct('BarObject')
        check_struct('BazObject')
        check_struct('NotAnObject')

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
