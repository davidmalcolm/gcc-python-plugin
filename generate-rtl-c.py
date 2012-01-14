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

from maketreetypes import iter_rtl_expr_types #, iter_rtl_struct_types

from cpybuilder import *
from wrapperbuilder import PyGccWrapperTypeObject

cu = CompilationUnit()
cu.add_include('gcc-python.h')
cu.add_include('gcc-python-wrappers.h')
cu.add_include('gcc-plugin.h')
cu.add_include("rtl.h")

modinit_preinit = ''
modinit_postinit = ''

#rtl_struct_types = list(iter_rtl_struct_types())
rtl_expr_types = list(iter_rtl_expr_types())
#print rtl_types

# Should be a three-level hierarchy:
#
# - Rtl base class
#   - intermediate subclasses, one per enum rtx_class
#     - concrete subclasses, one per enum rtx_code

def generate_rtl_base_class():
    #
    # Generate the gcc.Rtl class:
    #
    global modinit_preinit
    global modinit_postinit
    '''
    cu.add_defn("""
static PyObject *
gcc_Rtl_get_block(struct PyGccRtl *self, void *closure)
{
    return gcc_python_make_wrapper_tree(rtl_block(self->stmt));
}
""")
    '''
    getsettable = PyGetSetDefTable('gcc_Rtl_getset_table', [])
    getsettable.add_gsdef('loc',
                          'gcc_Rtl_get_location',
                          None,
                          'Source code location of this expression, as a gcc.Location')
    getsettable.add_gsdef('operands',
                          'gcc_Rtl_get_operands',
                          None,
                          'Operands of this expression, as a tuple')
    cu.add_defn(getsettable.c_defn())

    pytype = PyGccWrapperTypeObject(identifier = 'gcc_RtlType',
                          localname = 'Rtl',
                          tp_name = 'gcc.Rtl',
                          tp_dealloc = 'gcc_python_wrapper_dealloc',
                          struct_name = 'PyGccRtl',
                          tp_new = 'PyType_GenericNew',
                          tp_getset = getsettable.identifier,
                          tp_repr = '(reprfunc)gcc_Rtl_repr',
                          tp_str = '(reprfunc)gcc_Rtl_str',
                          )
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

generate_rtl_base_class()

# enum rtx_class from gcc/rtl.h (as seen in 4.6.0):
enum_rtx_class = ('RTX_COMPARE',
                  'RTX_COMM_COMPARE',
                  'RTX_BIN_ARITH',
                  'RTX_COMM_ARITH',
                  'RTX_UNARY',
                  'RTX_EXTRA',
                  'RTX_MATCH',
                  'RTX_INSN',
                  'RTX_OBJ',
                  'RTX_CONST_OBJ',
                  'RTX_TERNARY',
                  'RTX_BITFIELD_OPS',
                  'RTX_AUTOINC')

def generate_intermediate_rtx_class_subclasses():
    global modinit_preinit
    global modinit_postinit

    for rtx_class in enum_rtx_class:
        cc = camel_case(rtx_class)
        pytype = PyGccWrapperTypeObject(identifier = 'gcc_RtlClassType%sType' % cc,
                              localname = 'RtlClassType' + cc,
                              tp_name = 'gcc.%s' % cc,
                              struct_name = 'PyGccRtl',
                              tp_new = 'PyType_GenericNew',
                              tp_base = '&gcc_RtlType',
                              #tp_getset = getsettable.identifier,
                              #tp_repr = '(reprfunc)gcc_Rtl_repr',
                              #tp_str = '(reprfunc)gcc_Rtl_str',
                              )
        cu.add_defn(pytype.c_defn())
        modinit_preinit += pytype.c_invoke_type_ready()
        modinit_postinit += pytype.c_invoke_add_to_module()

generate_intermediate_rtx_class_subclasses()


def generate_concrete_rtx_code_subclasses():
    global modinit_preinit
    global modinit_postinit

    for expr_type in rtl_expr_types:

        cc = expr_type.camel_cased_string()

        getsettable = None
        if getsettable:
            cu.add_defn(getsettable.c_defn())

        pytype = PyGccWrapperTypeObject(identifier = 'gcc_%sType' % cc,
                              localname = cc,
                              tp_name = 'gcc.%s' % cc,
                              struct_name = 'PyGccRtl',
                              tp_new = 'PyType_GenericNew',
                              #tp_base = '&gcc_RtlType',
                              tp_base = ('&gcc_RtlClassType%sType'
                                         % camel_case(expr_type.CLASS)),
                              tp_getset = getsettable.identifier if getsettable else None,
                              tp_repr = '(reprfunc)gcc_Rtl_repr',
                              tp_str = '(reprfunc)gcc_Rtl_str',
                              )
        cu.add_defn(pytype.c_defn())
        modinit_preinit += pytype.c_invoke_type_ready()
        modinit_postinit += pytype.c_invoke_add_to_module()

generate_concrete_rtx_code_subclasses()

def generate_rtl_code_map():
    cu.add_defn('\n/* Map from GCC rtl codes to PyGccWrapperTypeObject* */\n')
    cu.add_defn('PyGccWrapperTypeObject *pytype_for_rtx_code[] = {\n')
    for expr_type in rtl_expr_types:
        cc = expr_type.camel_cased_string()
        cu.add_defn('    &gcc_%sType, /* %s */\n' % (cc, expr_type.ENUM))
    cu.add_defn('};\n\n')

    cu.add_defn("""
PyGccWrapperTypeObject*
gcc_python_autogenerated_rtl_type_for_stmt(struct rtx_def *insn)
{
    enum rtx_code code = insn->code;

    /* printf("code:%i\\n", code); */
    assert(code >= 0);
    assert(code < LAST_AND_UNUSED_RTX_CODE);
    return pytype_for_rtx_code[code];
}
""")

generate_rtl_code_map()

cu.add_defn("""
int autogenerated_rtl_init_types(void)
{
""" + modinit_preinit + """
    return 1;

error:
    return 0;
}
""")

cu.add_defn("""
void autogenerated_rtl_add_types(PyObject *m)
{
""" + modinit_postinit + """
}
""")


print(cu.as_str())

