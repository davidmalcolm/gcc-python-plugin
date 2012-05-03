#   Copyright 2011, 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011, 2012 Red Hat, Inc.
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

from cpybuilder import *
from wrapperbuilder import PyGccWrapperTypeObject

cu = CompilationUnit()
cu.add_include('gcc-python.h')
cu.add_include('gcc-python-wrappers.h')
cu.add_include('gcc-plugin.h')
cu.add_include("proposed-plugin-api/gcc-callgraph.h")
cu.add_include("proposed-plugin-api/gcc-gimple.h")

modinit_preinit = ''
modinit_postinit = ''

def generate_callgraph_edge():
    #
    # Generate the gcc.CallgraphEdge class:
    #
    global modinit_preinit
    global modinit_postinit

    getsettable = PyGetSetDefTable('gcc_CallgraphEdge_getset_table', [],
                                   identifier_prefix='gcc_CallgraphEdge',
                                   typename='PyGccCallgraphEdge')
    getsettable.add_simple_getter(cu,
                                  'caller',
                                  'gcc_python_make_wrapper_cgraph_node(gcc_cgraph_edge_get_caller(self->edge))',
                                  'The function that makes this call, as a gcc.CallgraphNode')
    getsettable.add_simple_getter(cu,
                                  'callee',
                                  'gcc_python_make_wrapper_cgraph_node(gcc_cgraph_edge_get_callee(self->edge))',
                                  'The function that is called here, as a gcc.CallgraphNode')
    getsettable.add_simple_getter(cu,
                                  'call_stmt',
                                  'gcc_python_make_wrapper_gimple(gcc_gimple_call_upcast(gcc_cgraph_edge_get_call_stmt(self->edge)))',
                                  'The gcc.GimpleCall statememt for the function call')
    cu.add_defn(getsettable.c_defn())

    pytype = PyGccWrapperTypeObject(identifier = 'gcc_CallgraphEdgeType',
                          localname = 'CallgraphEdge',
                          tp_name = 'gcc.CallgraphEdge',
                          struct_name = 'PyGccCallgraphEdge',
                          tp_new = 'PyType_GenericNew',
                          tp_getset = getsettable.identifier,
                          tp_repr = '(reprfunc)gcc_CallgraphEdge_repr',
                          tp_str = '(reprfunc)gcc_CallgraphEdge_str',
                          tp_dealloc = 'gcc_python_wrapper_dealloc',
                          )
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

generate_callgraph_edge()

def generate_callgraph_node():
    #
    # Generate the gcc.CallgraphNode class:
    #
    global modinit_preinit
    global modinit_postinit

    getsettable = PyGetSetDefTable('gcc_CallgraphNode_getset_table', [],
                                   identifier_prefix='gcc_CallgraphNode',
                                   typename='PyGccCallgraphNode')
    # FIXME: add getters
    getsettable.add_simple_getter(cu,
                                  'decl',
                                  'gcc_python_make_wrapper_tree(gcc_cgraph_node_get_decl(self->node).inner)',
                                  'The gcc.FunctionDecl for this node')
    getsettable.add_gsdef('callees',
                          'gcc_CallgraphNode_get_callees',
                          None,
                          'The function calls made by this function, as a list of gcc.CallgraphEdge')
    getsettable.add_gsdef('callers',
                          'gcc_CallgraphNode_get_callers',
                          None,
                          'The places that call this function, as a list of gcc.CallgraphEdge')
    cu.add_defn(getsettable.c_defn())

    # see gcc/cgraph.c: dump_cgraph_node (FILE *f, struct cgraph_node *node)

    pytype = PyGccWrapperTypeObject(identifier = 'gcc_CallgraphNodeType',
                          localname = 'CallgraphNode',
                          tp_name = 'gcc.CallgraphNode',
                          struct_name = 'PyGccCallgraphNode',
                          tp_new = 'PyType_GenericNew',
                          tp_getset = getsettable.identifier,
                          tp_repr = '(reprfunc)gcc_CallgraphNode_repr',
                          tp_str = '(reprfunc)gcc_CallgraphNode_str',
                          tp_dealloc = 'gcc_python_wrapper_dealloc',
                          )
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

generate_callgraph_node()

cu.add_defn("""
int autogenerated_callgraph_init_types(void)
{
""" + modinit_preinit + """
    return 1;

error:
    return 0;
}
""")

cu.add_defn("""
void autogenerated_callgraph_add_types(PyObject *m)
{
""" + modinit_postinit + """
}
""")



print(cu.as_str())
