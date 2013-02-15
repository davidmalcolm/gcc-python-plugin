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
cu.add_include("tree-pass.h")

modinit_preinit = ''
modinit_postinit = ''

# See GCC's tree-pass.h

def generate_pass():
    global modinit_preinit
    global modinit_postinit

    getsettable = PyGetSetDefTable('PyGccPass_getset_table', [],
                                   identifier_prefix='PyGccPass',
                                   typename='PyGccPass')
    getsettable.add_simple_getter(cu,
                                  'name',
                                  'PyGccString_FromString(self->pass->name)',
                                  'Name of the pass')
    getsettable.add_simple_getter(cu,
                                  'next',
                                  'PyGccPass_New(self->pass->next)',
                                  'The next gcc.Pass after this one, or None')
    getsettable.add_simple_getter(cu,
                                  'sub',
                                  'PyGccPass_New(self->pass->sub)',
                                  "The first sub-pass (gated by this pass' predicate, if any)")

    for field in ('properties_required', 'properties_provided', 'properties_destroyed'):
        getsettable.add_simple_getter(cu,
                                      field,
                                      'PyGccInt_FromLong(self->pass->%s)' % field,
                                      None)
    getsettable.add_simple_getter(cu,
                                  'static_pass_number',
                                  'PyGccInt_FromLong(self->pass->static_pass_number)',
                                  'Number of this pass, used as a fragment of the dump file name')
    getsettable.add_gsdef('dump_enabled',
                          'PyGccPass_get_dump_enabled',
                          'PyGccPass_set_dump_enabled',
                          '(boolean) Is dumping enabled for this pass?')
    cu.add_defn(getsettable.c_defn())

    methods = PyMethodTable('PyGccPass_methods', [])
    methods.add_method('get_roots',
                       'PyGccPass_get_roots',
                       'METH_CLASS | METH_VARARGS',
                       "Get a tuple of gcc.Pass instances, the roots of the compilation pass tree")
    methods.add_method('get_by_name',
                       '(PyCFunction)PyGccPass_get_by_name',
                       'METH_CLASS | METH_VARARGS | METH_KEYWORDS',
                       "Get the gcc.Pass instance for the pass with the given name, raising ValueError if it isn't found")
    methods.add_method('register_after',
                       '(PyCFunction)PyGccPass_register_after',
                       'METH_VARARGS | METH_KEYWORDS',
                       "Given the name of another pass, register this gcc.Pass to occur immediately after that other pass")
    methods.add_method('register_before',
                       '(PyCFunction)PyGccPass_register_before',
                       'METH_VARARGS | METH_KEYWORDS',
                       "Given the name of another pass, register this gcc.Pass to occur immediately before that other pass")
    methods.add_method('replace',
                       '(PyCFunction)PyGccPass_replace',
                       'METH_VARARGS | METH_KEYWORDS',
                       "Given the name of another pass, replace that pass with this gcc.Pass")

    cu.add_defn(methods.c_defn())
    
    pytype = PyGccWrapperTypeObject(identifier = 'PyGccPass_TypeObj',
                          localname = 'Pass',
                          tp_name = 'gcc.Pass',
                          tp_dealloc = 'PyGccWrapper_Dealloc',
                          struct_name = 'PyGccPass',
                          tp_new = 'PyType_GenericNew',
                          tp_getset = getsettable.identifier,
                          tp_repr = '(reprfunc)PyGccPass_repr',
                          tp_str = '(reprfunc)PyGccPass_repr',
                          tp_methods = methods.identifier,
                          tp_flags = '(Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE)',
                          )
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

generate_pass()

def generate_pass_subclasses():
    global modinit_preinit
    global modinit_postinit

    for opt_pass_type in ('GIMPLE_PASS', 'RTL_PASS',
                          'SIMPLE_IPA_PASS', 'IPA_PASS'):
        cc = camel_case(opt_pass_type)
        pytype = PyGccWrapperTypeObject(identifier = 'PyGcc%s_TypeObj' % cc,
                              localname = cc,
                              tp_name = 'gcc.%s' % cc,
                              tp_dealloc = 'PyGccWrapper_Dealloc',
                              struct_name = 'PyGccPass',
                              tp_new = 'PyType_GenericNew',
                              tp_init = 'PyGcc%s_init' % cc,
                              tp_base = '&PyGccPass_TypeObj',
                              tp_flags = '(Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE)'
                              )
        cu.add_defn(pytype.c_defn())
        modinit_preinit += pytype.c_invoke_type_ready()
        modinit_postinit += pytype.c_invoke_add_to_module()

generate_pass_subclasses()

cu.add_defn("""
int autogenerated_pass_init_types(void)
{
""" + modinit_preinit + """
    return 1;

error:
    return 0;
}
""")

cu.add_defn("""
void autogenerated_pass_add_types(PyObject *m)
{
""" + modinit_postinit + """
}
""")

print(cu.as_str())
