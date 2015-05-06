#   Copyright 2011-2012, 2015 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011-2012, 2015 Red Hat, Inc.
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
from testcpychecker import get_gcc_version
from wrapperbuilder import PyGccWrapperTypeObject

GCC_VERSION = get_gcc_version()

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
PyGccRtl_get_block(struct PyGccRtl *self, void *closure)
{
    return PyGccTree_New(rtl_block(self->stmt));
}
""")
    '''
    getsettable = PyGetSetDefTable('PyGccRtl_getset_table', [])
    if GCC_VERSION < 5000:
        getsettable.add_gsdef('loc',
                              'PyGccRtl_get_location',
                              None,
                              'Source code location of this instruction, as a gcc.Location')
    getsettable.add_gsdef('operands',
                          'PyGccRtl_get_operands',
                          None,
                          'Operands of this expression, as a tuple')
    cu.add_defn(getsettable.c_defn())

    pytype = PyGccWrapperTypeObject(identifier = 'PyGccRtl_TypeObj',
                          localname = 'Rtl',
                          tp_name = 'gcc.Rtl',
                          tp_dealloc = 'PyGccWrapper_Dealloc',
                          struct_name = 'PyGccRtl',
                          tp_new = 'PyType_GenericNew',
                          tp_getset = getsettable.identifier,
                          tp_repr = '(reprfunc)PyGccRtl_repr',
                          tp_str = '(reprfunc)PyGccRtl_str',
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
        pytype = PyGccWrapperTypeObject(identifier = 'PyGccRtlClassType%s_TypeObj' % cc,
                              localname = 'RtlClassType' + cc,
                              tp_name = 'gcc.%s' % cc,
                              struct_name = 'PyGccRtl',
                              tp_new = 'PyType_GenericNew',
                              tp_base = '&PyGccRtl_TypeObj',
                              #tp_getset = getsettable.identifier,
                              #tp_repr = '(reprfunc)PyGccRtl_repr',
                              #tp_str = '(reprfunc)PyGccRtl_str',
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

        pytype = PyGccWrapperTypeObject(identifier = 'PyGcc%s_TypeObj' % cc,
                              localname = cc,
                              tp_name = 'gcc.%s' % cc,
                              struct_name = 'PyGccRtl',
                              tp_new = 'PyType_GenericNew',
                              tp_base = ('&PyGccRtlClassType%s_TypeObj'
                                         % camel_case(expr_type.CLASS)),
                              tp_getset = getsettable.identifier if getsettable else None,
                              tp_repr = '(reprfunc)PyGccRtl_repr',
                              tp_str = '(reprfunc)PyGccRtl_str',
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
        cu.add_defn('    &PyGcc%s_TypeObj, /* %s */\n' % (cc, expr_type.ENUM))
    cu.add_defn('};\n\n')

    cu.add_defn("""
PyGccWrapperTypeObject*
PyGcc_autogenerated_rtl_type_for_stmt(gcc_rtl_insn insn)
{
    enum rtx_code code = insn.inner->code;

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

