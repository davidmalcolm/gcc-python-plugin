#   Copyright 2011-2014, 2017 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011-2014, 2017 Red Hat, Inc.
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
from testcpychecker import get_gcc_version
from wrapperbuilder import PyGccWrapperTypeObject

cu = CompilationUnit()
cu.add_include('gcc-python.h')
cu.add_include('gcc-python-wrappers.h')
cu.add_include('gcc-plugin.h')
cu.add_include("gcc-c-api/gcc-location.h")

modinit_preinit = ''
modinit_postinit = ''

def generate_location():
    #
    # Generate the gcc.Location class:
    #
    global modinit_preinit
    global modinit_postinit

    cu.add_defn("""
static PyObject *
PyGccLocation_get_file(struct PyGccLocation *self, void *closure)
{
    const char *filename = gcc_location_get_filename(self->loc);
    if (!filename) {
      Py_RETURN_NONE;
    }
    return PyGccString_FromString(filename);
}
""")

    cu.add_defn("""
static PyObject *
PyGccLocation_get_line(struct PyGccLocation *self, void *closure)
{
    return PyGccInt_FromLong(gcc_location_get_line(self->loc));
}
""")

    cu.add_defn("""
static PyObject *
PyGccLocation_get_column(struct PyGccLocation *self, void *closure)
{
    return PyGccInt_FromLong(gcc_location_get_column(self->loc));
}
""")
    if get_gcc_version() >= 7000:
        cu.add_defn("""
static PyObject *
PyGccLocation_get_caret(struct PyGccLocation *self, void *closure)
{
    return PyGccLocation_New(gcc_location_get_caret(self->loc));
}
""")
        cu.add_defn("""
static PyObject *
PyGccLocation_get_start(struct PyGccLocation *self, void *closure)
{
    return PyGccLocation_New(gcc_location_get_start(self->loc));
}
""")
        cu.add_defn("""
static PyObject *
PyGccLocation_get_finish(struct PyGccLocation *self, void *closure)
{
    return PyGccLocation_New(gcc_location_get_finish(self->loc));
}
""")

    getsettable = PyGetSetDefTable('PyGccLocation_getset_table',
                                   [PyGetSetDef('file', 'PyGccLocation_get_file', None, 'Name of the source file'),
                                    PyGetSetDef('line', 'PyGccLocation_get_line', None, 'Line number within source file'),
                                    PyGetSetDef('column', 'PyGccLocation_get_column', None, 'Column number within source file'),
                                    ],
                                   identifier_prefix='PyGccLocation',
                                   typename='PyGccLocation')
    if get_gcc_version() >= 7000:
        getsettable.gsdefs += [PyGetSetDef('caret', 'PyGccLocation_get_caret', None, 'Location of caret'),
                               PyGetSetDef('start', 'PyGccLocation_get_start', None, 'Starting location of range'),
                               PyGetSetDef('finish', 'PyGccLocation_get_finish', None, 'End location of range')]
    getsettable.add_simple_getter(cu,
                                  'in_system_header',
                                  'PyBool_FromLong(gcc_location_get_in_system_header(self->loc))',
                                  'Boolean: is this location within a system header?')
    cu.add_defn(getsettable.c_defn())

    methods = PyMethodTable('PyGccLocation_methods', [])
    if get_gcc_version() >= 5000:
        methods.add_method('offset_column',
                           '(PyCFunction)PyGccLocation_offset_column',
                           'METH_VARARGS',
                           "")
    cu.add_defn(methods.c_defn())

    pytype = PyGccWrapperTypeObject(identifier = 'PyGccLocation_TypeObj',
                          localname = 'Location',
                          tp_name = 'gcc.Location',
                          struct_name = 'PyGccLocation',
                          tp_new = 'PyType_GenericNew',
                          tp_init = '(initproc)PyGccLocation_init' if get_gcc_version() >= 7000 else None,
                          tp_getset = getsettable.identifier,
                          tp_hash = '(hashfunc)PyGccLocation_hash',
                          tp_repr = '(reprfunc)PyGccLocation_repr',
                          tp_str = '(reprfunc)PyGccLocation_str',
                          tp_methods = methods.identifier,
                          tp_richcompare = 'PyGccLocation_richcompare',
                          tp_dealloc = 'PyGccWrapper_Dealloc')
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

def generate_rich_location():
    #
    # Generate the gcc.RichLocation class:
    #

    # class rich_location was added to libcpp in gcc 6.
    GCC_VERSION = get_gcc_version()
    if GCC_VERSION < 6000:
        return

    global modinit_preinit
    global modinit_postinit

    methods = PyMethodTable('PyGccRichLocation_methods', [])
    methods.add_method('add_fixit_replace',
                       '(PyCFunction)PyGccRichLocation_add_fixit_replace',
                       'METH_VARARGS | METH_KEYWORDS',
                       "FIXME")
    cu.add_defn(methods.c_defn())

    pytype = PyGccWrapperTypeObject(identifier = 'PyGccRichLocation_TypeObj',
                          localname = 'RichLocation',
                          tp_name = 'gcc.RichLocation',
                          struct_name = 'PyGccRichLocation',
                          tp_new = 'PyType_GenericNew',
                          tp_init = '(initproc)PyGccRichLocation_init',
                          #tp_getset = getsettable.identifier,
                          #tp_hash = '(hashfunc)PyGccRichLocation_hash',
                          #tp_repr = '(reprfunc)PyGccRichLocation_repr',
                          #tp_str = '(reprfunc)PyGccRichLocation_str',
                          tp_methods = methods.identifier,
                          #tp_richcompare = 'PyGccRichLocation_richcompare',
                          tp_dealloc = 'PyGccWrapper_Dealloc')
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

generate_location()
generate_rich_location()

cu.add_defn("""
int autogenerated_location_init_types(void)
{
""" + modinit_preinit + """
    return 1;

error:
    return 0;
}
""")

cu.add_defn("""
void autogenerated_location_add_types(PyObject *m)
{
""" + modinit_postinit + """
}
""")



print(cu.as_str())
