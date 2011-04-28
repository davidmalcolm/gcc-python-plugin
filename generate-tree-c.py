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

def generate_pass():
    global modinit_preinit
    global modinit_postinit

    getsettable = PyGetSetDefTable('gcc_Pass_getset_table',
                                   [PyGetSetDef('name',
                                                cu.add_simple_getter('gcc_Pass_get_name',
                                                                     'PyGccPass',
                                                                     'PyString_FromString(self->pass->name)'),
                                                None,
                                                'Name of the pass'),
                                    ])
    cu.add_defn(getsettable.c_defn())
    
    pytype = PyTypeObject(identifier = 'gcc_PassType',
                          localname = 'Pass',
                          tp_name = 'gcc.Pass',
                          struct_name = 'struct PyGccPass',
                          tp_new = 'PyType_GenericNew',
                          tp_getset = getsettable.identifier,
                          )
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()
    
generate_pass()

def generate_pretty_printer():
    global modinit_preinit
    global modinit_postinit
    
    pytype = PyTypeObject(identifier = 'gcc_PrettyPrinterType',
                          localname = 'PrettyPrinter',
                          tp_name = 'gcc.PrettyPrinter',
                          struct_name = 'struct PyGccPrettyPrinter',
                          tp_new = 'PyType_GenericNew',
                          tp_dealloc = 'gcc_PrettyPrinter_dealloc',
                          )
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()
    
generate_pretty_printer()

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

    cu.add_defn("""
static PyObject *
gcc_Location_get_column(struct PyGccLocation *self, void *closure)
{
    expanded_location exploc = expand_location(self->loc);

    return PyInt_FromLong(exploc.column);
}
""")

    getsettable = PyGetSetDefTable('gcc_Location_getset_table',
                                   [PyGetSetDef('file', 'gcc_Location_get_file', None, 'Name of the source file'),
                                    PyGetSetDef('line', 'gcc_Location_get_line', None, 'Line number within source file'),
                                    PyGetSetDef('column', 'gcc_Location_get_column', None, 'Column number within source file'),
                                    ])
    cu.add_defn(getsettable.c_defn())

    pytype = PyTypeObject(identifier = 'gcc_LocationType',
                          localname = 'Location',
                          tp_name = 'gcc.Location',
                          struct_name = 'struct PyGccLocation',
                          tp_new = 'PyType_GenericNew',
                          tp_getset = getsettable.identifier,
                          tp_repr = '(reprfunc)gcc_Location_repr',
                          tp_str = '(reprfunc)gcc_Location_str',
                          tp_richcompare = 'gcc_Location_richcompare')
    cu.add_defn(pytype.c_defn())
    modinit_preinit += pytype.c_invoke_type_ready()
    modinit_postinit += pytype.c_invoke_add_to_module()

generate_location()

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
                                                                     'gcc_python_make_wrapper_basic_block(self->e->src)'),
                                                None,
                                                'The source gcc.BasicBlock of this edge'),
                                    PyGetSetDef('dest',
                                                cu.add_simple_getter('gcc_Edge_get_dest',
                                                                     'PyGccEdge',
                                                                     'gcc_python_make_wrapper_basic_block(self->e->dest)'),
                                                None,
                                                'The destination gcc.BasicBlock of this edge')])
    cu.add_defn(getsettable.c_defn())

    pytype = PyTypeObject(identifier = 'gcc_EdgeType',
                          localname = 'Edge',
                          tp_name = 'gcc.Edge',
                          struct_name = 'struct PyGccEdge',
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
                                    ])
    cu.add_defn(getsettable.c_defn())

    pytype = PyTypeObject(identifier = 'gcc_BasicBlockType',
                          localname = 'BasicBlock',
                          tp_name = 'gcc.BasicBlock',
                          struct_name = 'struct PyGccBasicBlock',
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
                                                                     'gcc_python_make_wrapper_basic_block(self->cfg->x_entry_block_ptr)'),
                                                None,
                                                'The initial gcc.BasicBlock in this graph'),
                                    PyGetSetDef('exit', 
                                                cu.add_simple_getter('gcc_Cfg_get_exit',
                                                                     'PyGccCfg',
                                                                     'gcc_python_make_wrapper_basic_block(self->cfg->x_exit_block_ptr)'),
                                                None,
                                                'The final gcc.BasicBlock in this graph'),
                                    ])
    cu.add_defn(getsettable.c_defn())
    pytype = PyTypeObject(identifier = 'gcc_CfgType',
                          localname = 'Cfg',
                          tp_name = 'gcc.Cfg',
                          struct_name = 'struct PyGccCfg',
                          tp_new = 'PyType_GenericNew',
                          #tp_repr = '(reprfunc)gcc_Cfg_repr',
                          #tp_str = '(reprfunc)gcc_Cfg_repr',
                          tp_getset = getsettable.identifier,
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
                                                'Instance of gcc.Cfg for this function (or None for early passes)'),
                                    ],
                                   identifier_prefix='gcc_Function',
                                   typename='PyGccFunction')
    getsettable.add_simple_getter(cu,
                                  'decl', 
                                  'gcc_python_make_wrapper_tree(self->fun->decl)',
                                  'The declaration of this function, as a gcc.Tree instance')
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
                          tp_getset = 'gcc_Tree_getset_table',
                          tp_str = '(reprfunc)gcc_Tree_str',
                          tp_richcompare = 'gcc_Tree_richcompare')
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

        getsettable = PyGetSetDefTable('gcc_%s_getset_table' % localname, [])

        pytype = PyTypeObject(identifier = code_type,
                              localname = localname,
                              tp_name = 'gcc.%s' % localname,
                              struct_name = 'struct PyGccTree',
                              tp_new = 'PyType_GenericNew',
                              tp_base = '&gcc_TreeType',
                              tp_getset = getsettable.identifier)
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

            getsettable.add_gsdef('name',
                                  'gcc_Declaration_get_name',
                                  None,
                                  'The name of this declaration (string)')
            getsettable.add_gsdef('function',
                                  'gcc_Declaration_get_function',
                                  None, 
                                  'The gcc.Function (or None) for this declaration')
            pytype.tp_repr = '(reprfunc)gcc_Declaration_repr'
            pytype.tp_str = '(reprfunc)gcc_Declaration_repr'

        def add_simple_getter(name, c_expression, doc):
            getsettable.add_gsdef(name,
                                  cu.add_simple_getter('gcc_%s_get_%s' % (localname, name),
                                                       'PyGccTree',
                                                       c_expression),
                                  None,
                                  doc)

        if localname == 'Type':
            add_simple_getter('name',
                              'gcc_python_make_wrapper_tree(TYPE_NAME(self->t))',
                              "The name of the type as a gcc.Tree, or None")

            methods = PyMethodTable('gcc_Type_methods', [])

            # Add the standard C integer types as properties.
            #
            # Tree nodes for the standard C integer types are defined in tree.h by
            #    extern GTY(()) tree integer_types[itk_none];
            # with macros to look into it of this form:
            #       #define unsigned_type_node    integer_types[itk_unsigned_int]
            #
            # The table is populated by tree.c:build_common_builtin_nodes
            # but unfortunately this seems to be called after our plugin is
            # initialized.
            #
            # Hence we add them as properties, so that they can be looked up on
            # demand, rather than trying to look them up once when the module
            # is set up
            for std_type in ('itk_char', 'itk_signed_char',
                             'itk_unsigned_char', 'itk_short',
                             'itk_unsigned_short', 'itk_int',
                             'itk_unsigned_int', 'itk_long',
                             'itk_unsigned_long', 'itk_long_long',
                             'itk_unsigned_long_long', 'itk_int128',
                             'itk_unsigned_int128'):
                # strip off the "itk_" prefix
                assert std_type.startswith('itk_')
                stddef = std_type[4:]
                #add_simple_getter(stddef,
                #                  'gcc_python_make_wrapper_tree(integer_types[%s])' % std_type,
                #                  "The builtin type '%s' as a gcc.Type (or None at startup before any compilation passes)" % stddef.replace('_', ' '))
                cu.add_defn(("""
PyObject*
%s(PyObject *cls, PyObject *args)
{
    return gcc_python_make_wrapper_tree(integer_types[%s]);
}
""")                           % ('gcc_Type_get_%s' % stddef,
                               std_type))
                methods.add_method('%s' % stddef,
                                   'gcc_Type_get_%s' % stddef,
                                   'METH_CLASS|METH_NOARGS',
                                   "The builtin type '%s' as a gcc.Type (or None at startup before any compilation passes)" % stddef.replace('_', ' '))
            pytype.tp_methods = methods.identifier
            cu.add_defn(methods.c_defn())
        cu.add_defn(getsettable.c_defn())            
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

        cc = tree_type.camel_cased_string()

        getsettable =  PyGetSetDefTable('gcc_%s_getset_table' % cc, [])

        def add_simple_getter(name, c_expression, doc):
            getsettable.add_gsdef(name,
                                  cu.add_simple_getter('gcc_%s_get_%s' % (cc, name),
                                                       'PyGccTree',
                                                       c_expression),
                                  None,
                                  doc)

        if cc == 'AddrExpr':
            add_simple_getter('operand',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND (self->t, 0))',
                              'The operand of this expression, as a gcc.Tree')

        if cc == 'StringCst':
            add_simple_getter('constant',
                              'PyString_FromString(TREE_STRING_POINTER(self->t))',
                              'The operand of this expression, as a gcc.Tree')

        # TYPE_QUALS for various foo_TYPE classes:
        if tree_type.SYM in ('VOID_TYPE', 'INTEGER_TYPE', 'REAL_TYPE', 
                             'FIXED_POINT_TYPE', 'COMPLEX_TYPE', 'VECTOR_TYPE',
                             'ENUMERAL_TYPE', 'BOOLEAN_TYPE'):
            for qual in ('const', 'volatile', 'restrict'):
                add_simple_getter(qual,
                                  'PyBool_FromLong(TYPE_QUALS(self->t) & TYPE_QUAL_%s)' % qual.upper(),
                                  "Boolean: does this type have the '%s' modifier?" % qual)

        if tree_type.SYM == 'INTEGER_TYPE':
            add_simple_getter('unsigned',
                              'PyBool_FromLong(TYPE_UNSIGNED(self->t))',
                              "Boolean: True for 'unsigned', False for 'signed'")
            add_simple_getter('precision',
                              'PyInt_FromLong(TYPE_PRECISION(self->t))',
                              'The precision of this type in bits, as an int (e.g. 32)')

        cu.add_defn(getsettable.c_defn())

        pytype = PyTypeObject(identifier = 'gcc_%sType' % cc,
                              localname = cc,
                              tp_name = 'gcc.%s' % cc,
                              struct_name = 'struct PyGccTree',
                              tp_new = 'PyType_GenericNew',
                              tp_base = '&%s' % base_type,
                              tp_getset = getsettable.identifier,
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
gcc_python_autogenerated_tree_type_for_tree_code(enum tree_code code, int borrow_ref)
{
    PyTypeObject *result;

    assert(code >= 0);
    assert(code < MAX_TREE_CODES);

    result = pytype_for_tree_code[code];

    if (!borrow_ref) {
        Py_INCREF(result);
    }
    return result;
}

PyTypeObject*
gcc_python_autogenerated_tree_type_for_tree(tree t, int borrow_ref)
{
    enum tree_code code = TREE_CODE(t);
    /* printf("code:%i\\n", code); */
    return gcc_python_autogenerated_tree_type_for_tree_code(code, borrow_ref);
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
