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
cu.add_include('gcc-c-api/gcc-cfg.h')
#cu.add_include("basic-block.h")

modinit_preinit = ''
modinit_postinit = ''

def generate_edge():
    #
    # Generate the gcc.Edge class:
    #
    global modinit_preinit
    global modinit_postinit

    getsettable = PyGetSetDefTable('PyGccEdge_getset_table',
                                   [PyGetSetDef('src',
                                                cu.add_simple_getter('PyGccEdge_get_src',
                                                                     'PyGccEdge',
                                                                     'PyGccBasicBlock_New(gcc_cfg_edge_get_src(self->e))'),
                                                None,
                                                'The source gcc.BasicBlock of this edge'),
                                    PyGetSetDef('dest',
                                                cu.add_simple_getter('PyGccEdge_get_dest',
                                                                     'PyGccEdge',
                                                                     'PyGccBasicBlock_New(gcc_cfg_edge_get_dest(self->e))'),
                                                None,
                                                'The destination gcc.BasicBlock of this edge')],
                                   identifier_prefix = 'PyGccEdge',
                                   typename = 'PyGccEdge')

    # We only expose the subset of the flags exposed by gcc-c-api
    for attrname, flaggetter in [('true_value', 'is_true_value'),
                                 ('false_value', 'is_false_value'),
                                 ('loop_exit', 'is_loop_exit'),
                                 ('can_fallthru', 'get_can_fallthru'),
                                 ('complex', 'is_complex'),
                                 ('eh', 'is_eh'),
                                 ]:
        getsettable.add_simple_getter(cu,
                                      attrname,
                                      'PyBool_FromLong(gcc_cfg_edge_%s(self->e))' % flaggetter,
                                      None)

    cu.add_defn(getsettable.c_defn())

    pytype = PyGccWrapperTypeObject(identifier = 'PyGccEdge_TypeObj',
                          localname = 'Edge',
                          tp_name = 'gcc.Edge',
                          tp_dealloc = 'PyGccWrapper_Dealloc',
                          struct_name = 'PyGccEdge',
                          tp_new = 'PyType_GenericNew',
                          #tp_repr = '(reprfunc)PyGccEdge_repr',
                          #tp_str = '(reprfunc)PyGccEdge_repr',
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

    getsettable = PyGetSetDefTable('PyGccBasicBlock_getset_table',
                                   [PyGetSetDef('preds',
                                                'PyGccBasicBlock_get_preds',
                                                None,
                                                'The list of predecessor gcc.Edge instances leading into this block'),
                                    PyGetSetDef('succs',
                                                'PyGccBasicBlock_get_succs',
                                                None,
                                                'The list of successor gcc.Edge instances leading out of this block'),
                                    PyGetSetDef('gimple',
                                                'PyGccBasicBlock_get_gimple',
                                                None,
                                                'The list of gcc.Gimple instructions, if appropriate for this pass, or None'),
                                    PyGetSetDef('phi_nodes',
                                                'PyGccBasicBlock_get_phi_nodes',
                                                None,
                                                'The list of gcc.GimplePhi phoney functions, if appropriate for this pass, or None'),
                                    PyGetSetDef('rtl',
                                                'PyGccBasicBlock_get_rtl',
                                                None,
                                                'The list of gcc.Rtl instructions, if appropriate for this pass, or None'),
                                    ],
                                   identifier_prefix='PyGccBasicBlock',
                                   typename='PyGccBasicBlock')
    getsettable.add_simple_getter(cu,
                                  'index',
                                  'PyGccInt_FromLong(gcc_cfg_block_get_index(self->bb))',
                                  None)
    cu.add_defn(getsettable.c_defn())

    pytype = PyGccWrapperTypeObject(identifier = 'PyGccBasicBlock_TypeObj',
                          localname = 'BasicBlock',
                          tp_name = 'gcc.BasicBlock',
                          tp_dealloc = 'PyGccWrapper_Dealloc',
                          struct_name = 'PyGccBasicBlock',
                          tp_new = 'PyType_GenericNew',
                          tp_repr = '(reprfunc)PyGccBasicBlock_repr',
                          #tp_str = '(reprfunc)PyGccBasicBlock_repr',
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

    getsettable = PyGetSetDefTable('PyGccCfg_getset_table',
                                   [PyGetSetDef('basic_blocks',
                                                'PyGccCfg_get_basic_blocks',
                                                None,
                                                'The list of gcc.BasicBlock instances in this graph'),
                                    PyGetSetDef('entry',
                                                cu.add_simple_getter('PyGccCfg_get_entry',
                                                                     'PyGccCfg',
                                                                     'PyGccBasicBlock_New(gcc_cfg_get_entry(self->cfg))'),
                                                None,
                                                'The initial gcc.BasicBlock in this graph'),
                                    PyGetSetDef('exit', 
                                                cu.add_simple_getter('PyGccCfg_get_exit',
                                                                     'PyGccCfg',
                                                                     'PyGccBasicBlock_New(gcc_cfg_get_exit(self->cfg))'),
                                                None,
                                                'The final gcc.BasicBlock in this graph'),
                                    ])
    cu.add_defn(getsettable.c_defn())
    pytype = PyGccWrapperTypeObject(identifier = 'PyGccCfg_TypeObj',
                          localname = 'Cfg',
                          tp_name = 'gcc.Cfg',
                          tp_dealloc = 'PyGccWrapper_Dealloc',
                          struct_name = 'PyGccCfg',
                          tp_new = 'PyType_GenericNew',
                          #tp_repr = '(reprfunc)PyGccCfg_repr',
                          #tp_str = '(reprfunc)PyGccCfg_repr',
                          tp_getset = getsettable.identifier,
                          )
    methods = PyMethodTable('PyGccCfg_methods', [])
    methods.add_method('get_block_for_label',
                       'PyGccCfg_get_block_for_label',
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
