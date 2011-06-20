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
cu.add_include("c-common.h")

modinit_preinit = ''
modinit_postinit = ''

def generate_tree():
    #
    # Generate the gcc.Tree class:
    #
    global modinit_preinit
    global modinit_postinit
    
    cu.add_defn("""
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
                                   [PyGetSetDef('type', 'gcc_Tree_get_type', None,
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
    methods = PyMethodTable('gcc_Tree_methods', [])
    methods.add_method('debug',
                       'gcc_Tree_debug',
                       'METH_VARARGS',
                       "Dump the tree to stderr")
    cu.add_defn("""
PyObject*
gcc_Tree_debug(PyObject *self, PyObject *args)
{
    PyGccTree *tree_obj;
    /* FIXME: type checking */
    tree_obj = (PyGccTree *)self;
    debug_tree(tree_obj->t);
    Py_RETURN_NONE;
}
""")
    cu.add_defn(methods.c_defn())
    pytype.tp_methods = methods.identifier

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
        return gcc_python_string_from_string(IDENTIFIER_POINTER (DECL_NAME (self->t)));
    }
    Py_RETURN_NONE;
}

static PyObject *
gcc_Declaration_get_location(struct PyGccTree *self, void *closure)
{
    return gcc_python_make_wrapper_location(DECL_SOURCE_LOCATION(self->t));
}
""")

            getsettable.add_gsdef('name',
                                  'gcc_Declaration_get_name',
                                  None,
                                  'The name of this declaration (string)')
            getsettable.add_gsdef('location',
                                  'gcc_Declaration_get_location',
                                  None,
                                  'The gcc.Location for this declaration')
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
            add_simple_getter('pointer',
                              'gcc_python_make_wrapper_tree(build_pointer_type(self->t))',
                              "The gcc.PointerType representing '(this_type *)'")

            methods = PyMethodTable('gcc_Type_methods', [])


            def add_type(c_expr_for_node, typename):
                # Expose the given global type node within the gcc.Tree API
                #
                # The table is populated by tree.c:build_common_builtin_nodes
                # but unfortunately this seems to be called after our plugin is
                # initialized.
                #
                # Hence we add them as properties, so that they can be looked up on
                # demand, rather than trying to look them up once when the module
                # is set up
                cu.add_defn("""
PyObject*
%s(PyObject *cls, PyObject *args)
{
    return gcc_python_make_wrapper_tree(%s);
}
"""                         % ('gcc_Type_get_%s' % typename, c_expr_for_node))
                if typename == 'size_t':
                    desc = typename
                else:
                    desc = typename.replace('_', ' ')
                methods.add_method('%s' % typename,
                                   'gcc_Type_get_%s' % typename,
                                   'METH_CLASS|METH_NOARGS',
                                   "The builtin type '%s' as a gcc.Type (or None at startup before any compilation passes)" % desc)

            # Add the standard C integer types as properties.
            #
            # Tree nodes for the standard C integer types are defined in tree.h by
            #    extern GTY(()) tree integer_types[itk_none];
            # with macros to look into it of this form:
            #       #define unsigned_type_node    integer_types[itk_unsigned_int]
            #
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
                add_type('integer_types[%s]' % std_type, stddef)

            # Similarly,
            #   extern GTY(()) tree global_trees[TI_MAX];
            # holds various nodes, including many with a _TYPE suffix.
            # Here are some of them:
            for ti in ('TI_UINT32_TYPE', 'TI_UINT64_TYPE',
                       'TI_FLOAT_TYPE', 'TI_DOUBLE_TYPE',
                       'TI_LONG_DOUBLE_TYPE', 'TI_VOID_TYPE', 'TI_SIZE_TYPE'):
                # strip off the "TI_" prefix and "_TYPE" suffix:
                assert ti.startswith('TI_')
                assert ti.endswith('_TYPE')

                if ti == 'TI_SIZE_TYPE':
                    name = 'size_t'
                else:
                    name = ti[3:-5].lower()
                add_type('global_trees[%s]' % ti, name)

            pytype.tp_methods = methods.identifier
            cu.add_defn(methods.c_defn())

        if localname == 'Expression':
            add_simple_getter('location',
                              'gcc_python_make_wrapper_location(EXPR_LOCATION(self->t))',
                              "The source location of this expression")

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

        def get_getter_identifier(name):
            return 'gcc_%s_get_%s' % (cc, name)

        def add_simple_getter(name, c_expression, doc):
            getsettable.add_gsdef(name,
                                  cu.add_simple_getter(get_getter_identifier(name),
                                                       'PyGccTree',
                                                       c_expression),
                                  None,
                                  doc)

        def add_complex_getter(name, doc):
            getsettable.add_gsdef(name,
                                  get_getter_identifier(name),
                                  None,
                                  doc)

        if cc == 'AddrExpr':
            add_simple_getter('operand',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND (self->t, 0))',
                              'The operand of this expression, as a gcc.Tree')

        if cc == 'StringCst':
            add_simple_getter('constant',
                              'gcc_python_string_from_string(TREE_STRING_POINTER(self->t))',
                              'The actual value of this constant, as a str')

        if cc == 'IntegerCst':
            getsettable.add_gsdef('constant',
                                  'gcc_IntegerConstant_get_constant',
                                  None,
                                  'The actual value of this constant, as an int/long')

        # TYPE_QUALS for various foo_TYPE classes:
        if tree_type.SYM in ('VOID_TYPE', 'INTEGER_TYPE', 'REAL_TYPE', 
                             'FIXED_POINT_TYPE', 'COMPLEX_TYPE', 'VECTOR_TYPE',
                             'ENUMERAL_TYPE', 'BOOLEAN_TYPE'):
            for qual in ('const', 'volatile', 'restrict'):
                add_simple_getter(qual,
                                  'PyBool_FromLong(TYPE_QUALS(self->t) & TYPE_QUAL_%s)' % qual.upper(),
                                  "Boolean: does this type have the '%s' modifier?" % qual)
                add_simple_getter('%s_equivalent' % qual,
                                  'gcc_python_make_wrapper_tree(build_qualified_type(self->t, TYPE_QUAL_%s))' % qual.upper(),
                                  'The gcc.Type for the %s version of this type' % qual)

        if tree_type.SYM == 'INTEGER_TYPE':
            add_simple_getter('unsigned',
                              'PyBool_FromLong(TYPE_UNSIGNED(self->t))',
                              "Boolean: True for 'unsigned', False for 'signed'")
            add_simple_getter('precision',
                              'gcc_python_int_from_long(TYPE_PRECISION(self->t))',
                              'The precision of this type in bits, as an int (e.g. 32)')
            add_simple_getter('signed_equivalent',
                              'gcc_python_make_wrapper_tree(c_common_signed_type(self->t))',
                              'The gcc.IntegerType for the signed version of this type')
            add_simple_getter('unsigned_equivalent',
                              'gcc_python_make_wrapper_tree(c_common_unsigned_type(self->t))',
                              'The gcc.IntegerType for the unsigned version of this type')
            add_simple_getter('max_value',
                              'gcc_python_make_wrapper_tree(TYPE_MAX_VALUE(self->t))',
                              'The maximum possible value for this type, as a gcc.IntegerCst')
            add_simple_getter('min_value',
                              'gcc_python_make_wrapper_tree(TYPE_MIN_VALUE(self->t))',
                              'The minimum possible value for this type, as a gcc.IntegerCst')

        if tree_type.SYM in ('POINTER_TYPE', 'ARRAY_TYPE', 'VECTOR_TYPE'):
            add_simple_getter('dereference',
                              'gcc_python_make_wrapper_tree(TREE_TYPE(self->t))',
                              "The gcc.Type that this type points to'")

        if tree_type.SYM == 'COMPONENT_REF':
            add_simple_getter('target',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND(self->t, 0))',
                              "The gcc.Node that for the container of the field'")
            add_simple_getter('field',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND(self->t, 1))',
                              "The gcc.Node for the field within the referenced thing'")

        if tree_type.SYM in ('RECORD_TYPE', 'UNION_TYPE', 'QUAL_UNION_TYPE'):
            add_simple_getter('fields',
                              'gcc_tree_list_from_chain(TYPE_FIELDS(self->t))',
                              "The fields of this type")

        if tree_type.SYM == 'IDENTIFIER_NODE':
            add_simple_getter('name',
                              'gcc_python_string_or_none(IDENTIFIER_POINTER(self->t))',
                              "The name of this gcc.IdentifierNode, as a string")

        if tree_type.SYM == 'VAR_DECL':
            add_simple_getter('initial',
                              'gcc_python_make_wrapper_tree(DECL_INITIAL(self->t))',
                              "The initial value for this variable as a gcc.Constructor, or None")

        if tree_type.SYM == 'CONSTRUCTOR':
            add_complex_getter('elements',
                              "The elements of this constructor, as a list of (index, gcc.Tree) pairs")

        if tree_type.SYM == 'TRANSLATION_UNIT_DECL':
            add_simple_getter('block',
                              'gcc_python_make_wrapper_tree(DECL_INITIAL(self->t))',
                               "The gcc.Block for this namespace")
            add_simple_getter('language',
                              'gcc_python_string_from_string(TRANSLATION_UNIT_LANGUAGE(self->t))',
                               "The source language of this translation unit, as a string")

        if tree_type.SYM == 'BLOCK':
            add_simple_getter('vars',
                              'gcc_tree_list_from_chain(BLOCK_VARS(self->t))',
                               "The list of gcc.Tree for the declarations and labels in this block")

        if tree_type.SYM == 'TYPE_DECL':
            add_simple_getter('pointer',
                              'gcc_python_make_wrapper_tree(build_pointer_type(self->t))',
                              "The gcc.PointerType representing '(this_type *)'")

        if tree_type.SYM == 'FUNCTION_TYPE':
            getsettable.add_gsdef('argument_types',
                                  'gcc_FunctionType_get_argument_types',
                                  None,
                                  "A tuple of gcc.Type instances, representing the argument types of this function type")

        if tree_type.SYM == 'FUNCTION_DECL':
            add_simple_getter('function',
                              'gcc_python_make_wrapper_function(DECL_STRUCT_FUNCTION(self->t))',
                              'The gcc.Function (or None) for this declaration')

        if tree_type.SYM == 'SSA_NAME':
            # c.f. "struct GTY(()) tree_ssa_name":
            add_simple_getter('var',
                              'gcc_python_make_wrapper_tree(SSA_NAME_VAR(self->t))',
                              "The variable being referenced'")
            add_simple_getter('def_stmt',
                              'gcc_python_make_wrapper_gimple(SSA_NAME_DEF_STMT(self->t))',
                              "The gcc.Gimple statement which defines this SSA name'")
            add_simple_getter('version',
                              'gcc_python_int_from_long(SSA_NAME_VERSION(self->t))',
                              "The SSA version number of this SSA name'")

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


generate_tree_code_classes()

cu.add_defn("""
int autogenerated_tree_init_types(void)
{
""" + modinit_preinit + """
    return 1;

error:
    return 0;
}
""")

cu.add_defn("""
void autogenerated_tree_add_types(PyObject *m)
{
""" + modinit_postinit + """
}
""")



print(cu.as_str())
