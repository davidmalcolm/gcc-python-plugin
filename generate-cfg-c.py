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
cu.add_include('proposed-plugin-api/gcc-cfg.h')
#cu.add_include("basic-block.h")

modinit_preinit = ''
modinit_postinit = ''

def generate_edge():
    #
    # Generate the gcc.Edge class:
    #
    global modinit_preinit
    global modinit_postinit

    getsettable = PyGetSetDefTable('gcc_Edge_getset_table',
                                   [PyGetSetDef('src',
                                                cu.add_simple_getter('gcc_Edge_get_src',
                                                                     'PyGccEdge',
                                                                     'gcc_python_make_wrapper_basic_block(GccCfgEdgeI_GetSrc(self->e))'),
                                                None,
                                                'The source gcc.BasicBlock of this edge'),
                                    PyGetSetDef('dest',
                                                cu.add_simple_getter('gcc_Edge_get_dest',
                                                                     'PyGccEdge',
                                                                     'gcc_python_make_wrapper_basic_block(GccCfgEdgeI_GetDest(self->e))'),
                                                None,
                                                'The destination gcc.BasicBlock of this edge')],
                                   identifier_prefix = 'gcc_Edge',
                                   typename = 'PyGccEdge')
    """
    for flag in ('EDGE_FALLTHRU', 'EDGE_ABNORMAL', 'EDGE_ABNORMAL_CALL',
                 'EDGE_EH', 'EDGE_FAKE', 'EDGE_DFS_BACK', 'EDGE_CAN_FALLTHRU',
                 'EDGE_IRREDUCIBLE_LOOP', 'EDGE_SIBCALL', 'EDGE_LOOP_EXIT',
                 'EDGE_TRUE_VALUE', 'EDGE_FALSE_VALUE', 'EDGE_EXECUTABLE',
                 'EDGE_CROSSING'):
        assert flag.startswith('EDGE_')
        flagname = flag[5:].lower()
        getsettable.add_simple_getter(cu,
                                      flagname,
                                      'PyBool_FromLong(gcc_edge_is_%s(self->e))' % flagname,
                                      'Boolean, corresponding to flag %s' % flag)
    """
    cu.add_defn(getsettable.c_defn())

    pytype = PyGccWrapperTypeObject(identifier = 'gcc_EdgeType',
                          localname = 'Edge',
                          tp_name = 'gcc.Edge',
                          tp_dealloc = 'gcc_python_wrapper_dealloc',
                          struct_name = 'PyGccEdge',
                          tp_new = 'PyType_GenericNew',
                          #tp_repr = '(reprfunc)gcc_Edge_repr',
                          #tp_str = '(reprfunc)gcc_Edge_repr',
                          tp_getset = getsettable.identifier,
                          )
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

generate_edge()

def generate_basic_block():
    #
    # Generate the gcc.BasicBlock class:
    #
    global modinit_preinit
    global modinit_postinit

    getsettable = PyGetSetDefTable('gcc_BasicBlock_getset_table',
                                   [PyGetSetDef('preds',
                                                'gcc_BasicBlock_get_preds',
                                                None,
                                                'The list of predecessor gcc.Edge instances leading into this block'),
                                    PyGetSetDef('succs',
                                                'gcc_BasicBlock_get_succs',
                                                None,
                                                'The list of successor gcc.Edge instances leading out of this block'),
                                    PyGetSetDef('gimple',
                                                'gcc_BasicBlock_get_gimple',
                                                None,
                                                'The list of gcc.Gimple instructions, if appropriate for this pass, or None'),
                                    PyGetSetDef('phi_nodes',
                                                'gcc_BasicBlock_get_phi_nodes',
                                                None,
                                                'The list of gcc.GimplePhi phoney functions, if appropriate for this pass, or None'),
                                    PyGetSetDef('rtl',
                                                'gcc_BasicBlock_get_rtl',
                                                None,
                                                'The list of gcc.Rtl instructions, if appropriate for this pass, or None'),
                                    ],
                                   identifier_prefix='gcc_BasicBlock',
                                   typename='PyGccBasicBlock')
    getsettable.add_simple_getter(cu,
                                  'index',
                                  'gcc_python_int_from_long(GccCfgBlockI_GetIndex(self->bb))',
                                  None)
    cu.add_defn(getsettable.c_defn())

    pytype = PyGccWrapperTypeObject(identifier = 'gcc_BasicBlockType',
                          localname = 'BasicBlock',
                          tp_name = 'gcc.BasicBlock',
                          tp_dealloc = 'gcc_python_wrapper_dealloc',
                          struct_name = 'PyGccBasicBlock',
                          tp_new = 'PyType_GenericNew',
                          #tp_repr = '(reprfunc)gcc_BasicBlock_repr',
                          #tp_str = '(reprfunc)gcc_BasicBlock_repr',
                          tp_getset = getsettable.identifier,
                          )
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

generate_basic_block()

def generate_cfg():
    #
    # Generate the gcc.Cfg class:
    #
    global modinit_preinit
    global modinit_postinit

    getsettable = PyGetSetDefTable('gcc_Cfg_getset_table',
                                   [PyGetSetDef('basic_blocks',
                                                'gcc_Cfg_get_basic_blocks',
                                                None,
                                                'The list of gcc.BasicBlock instances in this graph'),
                                    PyGetSetDef('entry',
                                                cu.add_simple_getter('gcc_Cfg_get_entry',
                                                                     'PyGccCfg',
                                                                     'gcc_python_make_wrapper_basic_block(GccCfgI_GetEntry(self->cfg))'),
                                                None,
                                                'The initial gcc.BasicBlock in this graph'),
                                    PyGetSetDef('exit', 
                                                cu.add_simple_getter('gcc_Cfg_get_exit',
                                                                     'PyGccCfg',
                                                                     'gcc_python_make_wrapper_basic_block(GccCfgI_GetExit(self->cfg))'),
                                                None,
                                                'The final gcc.BasicBlock in this graph'),
                                    ])
    cu.add_defn(getsettable.c_defn())
    pytype = PyGccWrapperTypeObject(identifier = 'gcc_CfgType',
                          localname = 'Cfg',
                          tp_name = 'gcc.Cfg',
                          tp_dealloc = 'gcc_python_wrapper_dealloc',
                          struct_name = 'PyGccCfg',
                          tp_new = 'PyType_GenericNew',
                          #tp_repr = '(reprfunc)gcc_Cfg_repr',
                          #tp_str = '(reprfunc)gcc_Cfg_repr',
                          tp_getset = getsettable.identifier,
                          )
    methods = PyMethodTable('gcc_Cfg_methods', [])
    methods.add_method('get_block_for_label',
                       'gcc_Cfg_get_block_for_label',
                       'METH_VARARGS',
                       "Given a gcc.LabelDecl, get the corresponding gcc.BasicBlock")
    cu.add_defn(methods.c_defn())
    pytype.tp_methods = methods.identifier

    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

generate_cfg()

cu.add_defn("""
int autogenerated_cfg_init_types(void)
{
""" + modinit_preinit + """
    return 1;

error:
    return 0;
}
""")

cu.add_defn("""
void autogenerated_cfg_add_types(PyObject *m)
{
""" + modinit_postinit + """
}
""")



print(cu.as_str())
