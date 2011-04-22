from maketreetypes import iter_tree_types

from cpybuilder import *

tree_types = list(iter_tree_types())
# FIXME: truncate the list, for ease of development:
#tree_types = list(iter_tree_types())[:3]

cu = CompilationUnit()
cu.add_include('gcc-python.h')
cu.add_include('gcc-python-wrappers.h')
cu.add_include('gcc-plugin.h')
cu.add_include("tree.h")

modinit_preinit = ''
modinit_postinit = ''

#
# Generate the gcc.Location class:
#
cu.add_defn("""
static PyObject *
gcc_Location_get_file(struct PyGccLocation *self, void *closure)
{
    return PyString_FromString(LOCATION_FILE(self->loc));
}
""")
cu.add_defn("""
static PyObject *
gcc_Location_get_line(struct PyGccLocation *self, void *closure)
{
    return PyInt_FromLong(LOCATION_LINE(self->loc));
}
""")

getsettable = PyGetSetDefTable('gcc_Location_getset_table',
                               [PyGetSetDef('file', 'gcc_Location_get_file', None, 'Name of the source file'),
                                PyGetSetDef('line', 'gcc_Location_get_line', None, 'Line number within source file')])
cu.add_defn(getsettable.c_defn())

pytype = PyTypeObject(name = 'gcc_Location',
                      localname = 'Location',
                      tp_name = 'gcc.Location',
                      struct_name = 'struct PyGccLocation',
                      tp_dealloc = 'NULL',
                      tp_repr = 'NULL',
                      tp_methods = 'NULL',
                      tp_init = 'NULL',
                      tp_new = 'PyType_GenericNew')
cu.add_defn(pytype.c_defn())
modinit_preinit += "\n    %s.tp_getset = gcc_Location_getset_table;\n" % pytype.name
modinit_preinit += "\n    %s.tp_repr = (reprfunc)gcc_Location_repr;\n" % pytype.name
modinit_preinit += "\n    %s.tp_str = (reprfunc)gcc_Location_str;\n" % pytype.name
modinit_preinit += pytype.c_invoke_type_ready()
modinit_postinit += pytype.c_invoke_add_to_module()

#
# Generate the gcc.Tree class:
#

cu.add_defn("""
static PyObject *
gcc_Tree_get_location(struct PyGccTree *self, void *closure)
{
    return gcc_python_make_wrapper_location(DECL_SOURCE_LOCATION(self->t));
}
""")

getsettable = PyGetSetDefTable('gcc_Tree_getset_table',
                               [PyGetSetDef('location', 'gcc_Tree_get_location', None, 'Location')])
cu.add_defn(getsettable.c_defn())

pytype = PyTypeObject(name = 'gcc_TreeType',
                      localname = 'Tree',
                      tp_name = 'gcc.Tree',
                      struct_name = 'struct PyGccTree',
                      tp_dealloc = 'NULL',
                      tp_repr = 'NULL',
                      tp_methods = 'NULL',
                      tp_init = 'NULL',
                      tp_new = 'PyType_GenericNew')
cu.add_defn(pytype.c_defn())
modinit_preinit += "\n    %s.tp_getset = gcc_Tree_getset_table;\n" % pytype.name
modinit_preinit += pytype.c_invoke_type_ready()
modinit_postinit += pytype.c_invoke_add_to_module()

# Generate a "middle layer" of gcc.Tree subclasses, corresponding to most of the
# values of
#    enum_tree_code_class
# from GCC's tree.h

type_for_code_class = {
    'tcc_exceptional' : 'gcc_TreeType',
    'tcc_constant' : 'gcc_ConstantType',
    'tcc_type' : 'gcc_TypeType',
    'tcc_declaration' : 'gcc_DeclarationType',
    'tcc_reference' : 'gcc_ReferenceType',
    'tcc_comparison' : 'gcc_ComparisonType',
    'tcc_unary' : 'gcc_UnaryType',
    'tcc_binary' : 'gcc_BinaryType',
    'tcc_statement' : 'gcc_StatementType',
    'tcc_vl_exp' : 'gcc_VlExpType',
    'tcc_expression' : 'gcc_ExpressionType',
}

for code_type in type_for_code_class.values():
    # We've already built the base class:
    if code_type == 'gcc_TreeType':
        continue

    # Strip off the "gcc_" prefix and "Type" suffix:
    localname = code_type[4:-4]
    pytype = PyTypeObject(name = code_type,
                          localname = localname,
                          tp_name = 'gcc.%s' % localname,
                          struct_name = 'struct PyGccTree',
                          tp_dealloc = 'NULL',
                          tp_repr = 'NULL',
                          tp_methods = 'NULL',
                          tp_init = 'NULL',
                          tp_new = 'PyType_GenericNew')
    cu.add_defn(pytype.c_defn())

    if localname == 'Declaration':
        cu.add_defn("""
static PyObject *
gcc_Declaration_get_name(struct PyGccTree *self, void *closure)
{
    if (DECL_NAME(self->t)) {
        return PyString_FromString(IDENTIFIER_POINTER (DECL_NAME (self->t)));
    }
    Py_RETURN_NONE;
}
""")
        getsettable = PyGetSetDefTable('gcc_Declaration_getset_table',
                                       [PyGetSetDef('name', 'gcc_Declaration_get_name', None, 'Location')])
        cu.add_defn(getsettable.c_defn())
        modinit_preinit += "\n    %s.tp_getset = %s;\n" % (code_type, 'gcc_Declaration_getset_table')
        
    modinit_preinit += "\n    %s.tp_base = &%s;\n" % (code_type, 'gcc_TreeType')
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()



# Generate all of the concrete gcc.Tree subclasses based on the:
#    enum tree_code
# as subclasses of the above layer:

for tree_type in tree_types:
    base_type = type_for_code_class[tree_type.TYPE]
    pytype = PyTypeObject(name = 'gcc_%sType' % tree_type.camel_cased_string(),
                          localname = tree_type.camel_cased_string(),
                          tp_name = 'gcc.%s' % tree_type.camel_cased_string(),
                          struct_name = 'struct PyGccTree',
                          tp_dealloc = 'NULL',
                          tp_repr = 'NULL',
                          tp_methods = 'NULL',
                          tp_init = 'NULL',
                          tp_new = 'PyType_GenericNew')
    cu.add_defn(pytype.c_defn())
    modinit_preinit += "\n    %s.tp_base = &%s;\n" % (pytype.name, base_type)
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()


cu.add_defn('\n/* Map from GCC tree codes to PyTypeObject* */\n')
cu.add_defn('PyTypeObject *pytype_for_tree_code[] = {\n')
for tree_type in tree_types:
    cu.add_defn('    &gcc_%sType, /* %s */\n' % (tree_type.camel_cased_string(), tree_type.SYM))
cu.add_defn('};\n\n')
cu.add_defn("""
PyTypeObject*
gcc_python_autogenerated_tree_type_for_tree(tree t)
{
    enum tree_code code = TREE_CODE(t);
    /* printf("code:%i\\n", code); */
    /* FIXME: range check */
    return pytype_for_tree_code[code];
}
""")


cu.add_defn("""
int gcc_python_autogenerated_tree_init_types(void)
{
""" + modinit_preinit + """
    return 1;

error:
    return 0;
}
""")

cu.add_defn("""
void gcc_python_autogenerated_tree_add_types(PyObject *m)
{
""" + modinit_postinit + """
}
""")

print(cu.as_str())
