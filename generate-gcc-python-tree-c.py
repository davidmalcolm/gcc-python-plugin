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
cu.add_include("function.h")
cu.add_include("basic-block.h")

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

    pytype = PyTypeObject(identifier = 'gcc_LocationType',
                          localname = 'Location',
                          tp_name = 'gcc.Location',
                          struct_name = 'struct PyGccLocation',
                          tp_new = 'PyType_GenericNew',
                          tp_getset = getsettable.identifier,
                          tp_repr = '(reprfunc)gcc_Location_repr',
                          tp_str = '(reprfunc)gcc_Location_str')
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

generate_location()

def generate_cfg():
    #
    # Generate the gcc.Cfg class:
    #
    global modinit_preinit
    global modinit_postinit

    pytype = PyTypeObject(identifier = 'gcc_CfgType',
                          localname = 'Cfg',
                          tp_name = 'gcc.Cfg',
                          struct_name = 'struct PyGccCfg',
                          tp_new = 'PyType_GenericNew',
                          #tp_repr = '(reprfunc)gcc_Cfg_repr',
                          #tp_str = '(reprfunc)gcc_Cfg_repr',
                          )
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

generate_cfg()

def generate_function():
    #
    # Generate the gcc.Function class:
    #
    global modinit_preinit
    global modinit_postinit
    cu.add_defn("\n"
                "static PyObject *\n"
                "gcc_Function_get_cfg(struct PyGccFunction *self, void *closure)\n"
                "{\n"
                "    return gcc_python_make_wrapper_cfg(self->fun->cfg);\n"
                "}\n"
                "\n")
    getsettable = PyGetSetDefTable('gcc_Function_getset_table',
                                   [PyGetSetDef('cfg', 'gcc_Function_get_cfg', None,
                                                'Instance of gcc.Cfg for this function (or None for early passes)')])
    cu.add_defn(getsettable.c_defn())

    pytype = PyTypeObject(identifier = 'gcc_FunctionType',
                          localname = 'Function',
                          tp_name = 'gcc.Function',
                          struct_name = 'struct PyGccFunction',
                          tp_new = 'PyType_GenericNew',
                          tp_repr = '(reprfunc)gcc_Function_repr',
                          tp_str = '(reprfunc)gcc_Function_repr',
                          tp_getset = getsettable.identifier)
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

generate_function()

def generate_tree():
    #
    # Generate the gcc.Tree class:
    #
    global modinit_preinit
    global modinit_postinit
    
    cu.add_defn("""
static PyObject *
gcc_Tree_get_location(struct PyGccTree *self, void *closure)
{
    return gcc_python_make_wrapper_location(DECL_SOURCE_LOCATION(self->t));
}

static PyObject *
gcc_Tree_get_type(struct PyGccTree *self, void *closure)
{
    return gcc_python_make_wrapper_tree(TREE_TYPE(self->t));
}

static PyObject *
gcc_Tree_get_addr(struct PyGccTree *self, void *closure)
{
    return PyLong_FromVoidPtr(self->t);
}

""")

    getsettable = PyGetSetDefTable('gcc_Tree_getset_table',
                                   [PyGetSetDef('location', 'gcc_Tree_get_location', None,
                                                'Instance of gcc.Location indicating the source code location of this node'),
                                    PyGetSetDef('type', 'gcc_Tree_get_type', None,
                                                'Instance of gcc.Tree giving the type of the node'),
                                    PyGetSetDef('addr', 'gcc_Tree_get_addr', None,
                                                'The address of the underlying GCC object in memory')])
    cu.add_defn(getsettable.c_defn())
    
    pytype = PyTypeObject(identifier = 'gcc_TreeType',
                          localname = 'Tree',
                          tp_name = 'gcc.Tree',
                          struct_name = 'struct PyGccTree',
                          tp_new = 'PyType_GenericNew',
                          tp_getset = 'gcc_Tree_getset_table')
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()
    
generate_tree()

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

def generate_intermediate_tree_classes():
    # Generate a "middle layer" of gcc.Tree subclasses, corresponding to most of the
    # values of
    #    enum_tree_code_class
    # from GCC's tree.h
    global modinit_preinit
    global modinit_postinit

    
    for code_type in type_for_code_class.values():
        # We've already built the base class:
        if code_type == 'gcc_TreeType':
            continue

        # Strip off the "gcc_" prefix and "Type" suffix:
        localname = code_type[4:-4]
        pytype = PyTypeObject(identifier = code_type,
                              localname = localname,
                              tp_name = 'gcc.%s' % localname,
                              struct_name = 'struct PyGccTree',
                              tp_new = 'PyType_GenericNew',
                              tp_base = '&gcc_TreeType')
        if localname == 'Declaration':
            cu.add_defn("""
PyObject *
gcc_Declaration_get_name(struct PyGccTree *self, void *closure)
{
    if (DECL_NAME(self->t)) {
        return PyString_FromString(IDENTIFIER_POINTER (DECL_NAME (self->t)));
    }
    Py_RETURN_NONE;
}

PyObject *
gcc_Declaration_get_function(struct PyGccTree *self, void *closure)
{
    assert(CODE_CONTAINS_STRUCT (TREE_CODE(self->t), TS_DECL_COMMON));

    return gcc_python_make_wrapper_function(DECL_STRUCT_FUNCTION(self->t));
}
""")
            getsettable = PyGetSetDefTable('gcc_Declaration_getset_table',
                                           [PyGetSetDef('name', 'gcc_Declaration_get_name', None, 'The name of this declaration (string)'),
                                            PyGetSetDef('function', 'gcc_Declaration_get_function', None, 'The gcc.Function (or None) for this declaration')])

            cu.add_defn(getsettable.c_defn())
            pytype.tp_getset = getsettable.identifier
            pytype.tp_repr = '(reprfunc)gcc_Declaration_repr'
            pytype.tp_str = '(reprfunc)gcc_Declaration_repr'
            
        cu.add_defn(pytype.c_defn())
        modinit_preinit += pytype.c_invoke_type_ready()
        modinit_postinit += pytype.c_invoke_add_to_module()

generate_intermediate_tree_classes()


def generate_tree_code_classes():
    # Generate all of the concrete gcc.Tree subclasses based on the:
    #    enum tree_code
    # as subclasses of the above layer:
    global modinit_preinit
    global modinit_postinit
    
    for tree_type in tree_types:
        base_type = type_for_code_class[tree_type.TYPE]
        pytype = PyTypeObject(identifier = 'gcc_%sType' % tree_type.camel_cased_string(),
                              localname = tree_type.camel_cased_string(),
                              tp_name = 'gcc.%s' % tree_type.camel_cased_string(),
                              struct_name = 'struct PyGccTree',
                              tp_new = 'PyType_GenericNew',
                              tp_base = '&%s' % base_type
                              )
        cu.add_defn(pytype.c_defn())
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
    assert(code >= 0);
    assert(code < MAX_TREE_CODES);
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

generate_tree_code_classes()

print(cu.as_str())
