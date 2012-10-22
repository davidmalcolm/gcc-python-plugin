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

from maketreetypes import iter_tree_types

from cpybuilder import *
from wrapperbuilder import PyGccWrapperTypeObject

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
cu.add_include("cp/cp-tree.h")
cu.add_include("c-family/c-common.h")
cu.add_include("cp/name-lookup.h")

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
                                                'The address of the underlying GCC object in memory'),
                                    PyGetSetDef('str_no_uid', 'gcc_Tree_get_str_no_uid', None,
                                                'A string representation of this object, like str(), but without including any internal UID')],
                                   identifier_prefix='gcc_Tree',
                                   typename='PyGccTree')

    cu.add_defn(getsettable.c_defn())
    
    pytype = PyGccWrapperTypeObject(identifier = 'gcc_TreeType',
                          localname = 'Tree',
                          tp_name = 'gcc.Tree',
                          tp_dealloc = 'gcc_python_wrapper_dealloc',
                          struct_name = 'PyGccTree',
                          tp_new = 'PyType_GenericNew',
                          tp_getset = 'gcc_Tree_getset_table',
                          tp_hash = '(hashfunc)gcc_Tree_hash',
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

        methods = PyMethodTable('gcc_%s_methods' % localname, [])

        pytype = PyGccWrapperTypeObject(identifier = code_type,
                              localname = localname,
                              tp_name = 'gcc.%s' % localname,
                              struct_name = 'PyGccTree',
                              tp_new = 'PyType_GenericNew',
                              tp_base = '&gcc_TreeType',
                              tp_getset = getsettable.identifier,
                              tp_methods = methods.identifier)

        def add_simple_getter(name, c_expression, doc):
            getsettable.add_gsdef(name,
                                  cu.add_simple_getter('gcc_%s_get_%s' % (localname, name),
                                                       'PyGccTree',
                                                       c_expression),
                                  None,
                                  doc)

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
            add_simple_getter('is_artificial',
                              'PyBool_FromLong(DECL_ARTIFICIAL(self->t))',
                              "Is this a compiler-generated entity?")
            add_simple_getter('is_builtin',
                              'PyBool_FromLong(DECL_IS_BUILTIN(self->t))',
                              "Is this declaration built in by the compiler?")
            pytype.tp_repr = '(reprfunc)gcc_Declaration_repr'

        if localname == 'Type':
            add_simple_getter('name',
                              'gcc_python_make_wrapper_tree(TYPE_NAME(self->t))',
                              "The name of the type as a gcc.Tree, or None")
            add_simple_getter('pointer',
                              'gcc_python_make_wrapper_tree(build_pointer_type(self->t))',
                              "The gcc.PointerType representing '(this_type *)'")
            getsettable.add_gsdef('attributes',
                                  'gcc_Type_get_attributes',
                                  None,
                                  'The user-defined attributes on this type')
            getsettable.add_gsdef('sizeof',
                                  'gcc_Type_get_sizeof',
                                  None,
                                  'sizeof() this type, as a gcc.IntegerCst')

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

        if localname == 'Unary':
            add_simple_getter('operand',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND (self->t, 0))',
                              'The operand of this expression, as a gcc.Tree')

        # Corresponds to this gcc/tree.h macro:
        #   #define IS_EXPR_CODE_CLASS(CLASS)\
        #       ((CLASS) >= tcc_reference && (CLASS) <= tcc_expression)
        if localname in ('Reference', 'Comparison', 'Unary', 'Binary',
                         'Statement' 'VlExp', 'Expression'):
            add_simple_getter('location',
                              'gcc_python_make_wrapper_location(EXPR_LOCATION(self->t))',
                              "The source location of this expression")

            methods.add_method('get_symbol',
                               'gcc_Tree_get_symbol', # they all share the implementation
                               'METH_CLASS|METH_NOARGS',
                               "FIXME")

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

        getsettable =  PyGetSetDefTable('gcc_%s_getset_table' % cc, [],
                                        identifier_prefix='gcc_%s' % cc,
                                        typename='PyGccTree')

        tp_as_number = None
        tp_repr = None
        tp_str = None

        methods = PyMethodTable('gcc_%s_methods' % cc, [])

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
            tp_repr = '(reprfunc)gcc_StringConstant_repr'

        if cc == 'IntegerCst':
            getsettable.add_gsdef('constant',
                                  'gcc_IntegerConstant_get_constant',
                                  None,
                                  'The actual value of this constant, as an int/long')
            number_methods = PyNumberMethods('gcc_IntegerConstant_number_methods')
            tp_as_number = number_methods.identifier
            number_methods.nb_int = 'gcc_IntegerConstant_get_constant'
            cu.add_defn(number_methods.c_defn())
            tp_repr = '(reprfunc)gcc_IntegerConstant_repr'

        if cc == 'RealCst':
            getsettable.add_gsdef('constant',
                                  'gcc_RealCst_get_constant',
                                  None,
                                  'The actual value of this constant, as a float')
            tp_repr = '(reprfunc)gcc_RealCst_repr'

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
            add_complex_getter('signed_equivalent',
                              'The gcc.IntegerType for the signed version of this type')
            add_complex_getter('unsigned_equivalent',
                              'The gcc.IntegerType for the unsigned version of this type')
            add_simple_getter('max_value',
                              'gcc_python_make_wrapper_tree(TYPE_MAX_VALUE(self->t))',
                              'The maximum possible value for this type, as a gcc.IntegerCst')
            add_simple_getter('min_value',
                              'gcc_python_make_wrapper_tree(TYPE_MIN_VALUE(self->t))',
                              'The minimum possible value for this type, as a gcc.IntegerCst')

        if tree_type.SYM in ('INTEGER_TYPE', 'REAL_TYPE', 'FIXED_POINT_TYPE'):
            add_simple_getter('precision',
                              'gcc_python_int_from_long(TYPE_PRECISION(self->t))',
                              'The precision of this type in bits, as an int (e.g. 32)')

        if tree_type.SYM in ('POINTER_TYPE', 'ARRAY_TYPE', 'VECTOR_TYPE'):
            add_simple_getter('dereference',
                              'gcc_python_make_wrapper_tree(TREE_TYPE(self->t))',
                              "The gcc.Type that this type points to'")

        if tree_type.SYM == 'ARRAY_TYPE':
            add_simple_getter('range',
                              'gcc_python_make_wrapper_tree(TYPE_DOMAIN(self->t))',
                              "The gcc.Type that is the range of this array type")

        if tree_type.SYM == 'ARRAY_REF':
            add_simple_getter('array',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND(self->t, 0))',
                              "The gcc.Tree for the array being referenced'")
            add_simple_getter('index',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND(self->t, 1))',
                              "The gcc.Tree for index being referenced'")

        if tree_type.SYM == 'COMPONENT_REF':
            add_simple_getter('target',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND(self->t, 0))',
                              "The gcc.Tree that for the container of the field'")
            add_simple_getter('field',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND(self->t, 1))',
                              "The gcc.FieldDecl for the field within the target'")

        if tree_type.SYM == 'MEM_REF':
            add_simple_getter('operand',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND(self->t, 0))',
                              "The gcc.Tree that for the pointer expression'")

        if tree_type.SYM == 'BIT_FIELD_REF':
            add_simple_getter('operand',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND(self->t, 0))',
                              "The gcc.Tree for the structure or union expression")
            add_simple_getter('num_bits',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND(self->t, 1))',
                              "The number of bits being referenced, as a gcc.IntegerCst")
            add_simple_getter('position',
                              'gcc_python_make_wrapper_tree(TREE_OPERAND(self->t, 2))',
                              "The position of the first referenced bit, as a gcc.IntegerCst")

        if tree_type.SYM in ('RECORD_TYPE', 'UNION_TYPE', 'QUAL_UNION_TYPE'):
            add_simple_getter('fields',
                              'gcc_tree_list_from_chain(TYPE_FIELDS(self->t))',
                              "The fields of this type")

        if tree_type.SYM == 'IDENTIFIER_NODE':
            add_simple_getter('name',
                              'gcc_python_string_or_none(IDENTIFIER_POINTER(self->t))',
                              "The name of this gcc.IdentifierNode, as a string")
            tp_repr = '(reprfunc)gcc_IdentifierNode_repr'

        if tree_type.SYM == 'VAR_DECL':
            add_simple_getter('initial',
                              'gcc_python_make_wrapper_tree(DECL_INITIAL(self->t))',
                              "The initial value for this variable as a gcc.Constructor, or None")
            add_simple_getter('static',
                              'PyBool_FromLong(TREE_STATIC(self->t))',
                              "Boolean: is this variable to be allocated with static storage")

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

        if tree_type.SYM == 'NAMESPACE_DECL':
            add_simple_getter('alias_of',
                              'gcc_python_make_wrapper_tree(DECL_NAMESPACE_ALIAS(self->t))',
                              "None if not an alias, otherwise the gcc.NamespaceDecl we alias")
            add_simple_getter('declarations',
                              'gcc_python_namespace_decl_declarations(self->t)',
                              'The list of gcc.Declarations within this namespace')
            add_simple_getter('namespaces',
                              'gcc_python_namespace_decl_namespaces(self->t)',
                              'The list of gcc.NamespaceDecl objects and gcc.TypeDecl of Unions nested in this namespace')
            methods.add_method('lookup',
                               '(PyCFunction)gcc_NamespaceDecl_lookup',
                               'METH_VARARGS|METH_KEYWORDS',
                               "Look up the given string within this namespace")
            methods.add_method('unalias',
                               '(PyCFunction)gcc_NamespaceDecl_unalias',
                               'METH_VARARGS|METH_KEYWORDS',
                               "A gcc.NamespaceDecl of this namespace that is not an alias")

        if tree_type.SYM == 'TYPE_DECL':
            getsettable.add_gsdef('pointer',
                                  'gcc_TypeDecl_get_pointer',
                                  None,
                                  "The gcc.PointerType representing '(this_type *)'")

        if tree_type.SYM == 'FUNCTION_TYPE':
            getsettable.add_gsdef('argument_types',
                                  'gcc_FunctionType_get_argument_types',
                                  None,
                                  "A tuple of gcc.Type instances, representing the argument types of this function type")

        if tree_type.SYM == 'METHOD_TYPE':
            getsettable.add_gsdef('argument_types',
                                  'gcc_MethodType_get_argument_types',
                                  None,
                                  "A tuple of gcc.Type instances, representing the argument types of this method type")

        if tree_type.SYM == 'FUNCTION_DECL':
            getsettable.add_gsdef('fullname',
                                  'gcc_FunctionDecl_get_fullname',
                                  None,
                                  'C++ only: the full name of this function declaration')
            add_simple_getter('function',
                              'gcc_python_make_wrapper_function(DECL_STRUCT_FUNCTION(self->t))',
                              'The gcc.Function (or None) for this declaration')
            add_simple_getter('arguments',
                              'gcc_tree_list_from_chain(DECL_ARGUMENTS(self->t))',
                              'List of gcc.ParmDecl')
            add_simple_getter('result',
                              'gcc_python_make_wrapper_tree(DECL_RESULT_FLD(self->t))',
                              'The gcc.ResultDecl for the return value')
            add_simple_getter('callgraph_node',
                              'gcc_python_make_wrapper_cgraph_node(cgraph_get_node(self->t))',
                              'The gcc.CallgraphNode for this function declaration, or None')

            for attr in ('public', 'private', 'protected', 'static'):
                getsettable.add_simple_getter(cu,
                                              'is_%s' % attr,
                                              'PyBool_FromLong(TREE_%s(self->t))' % attr.upper(),
                                              None)

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
            tp_repr = '(reprfunc)gcc_SsaName_repr'


        if tree_type.SYM == 'TREE_LIST':
            # c.f. "struct GTY(()) tree_list":
            tp_repr = '(reprfunc)gcc_TreeList_repr'

        if tree_type.SYM == 'CASE_LABEL_EXPR':
            add_simple_getter('low',
                              'gcc_python_make_wrapper_tree(CASE_LOW(self->t))',
                              "The low value of the case label, as a gcc.Tree (or None for the default)")
            add_simple_getter('high',
                              'gcc_python_make_wrapper_tree(CASE_HIGH(self->t))',
                              "The high value of the case label, if any, as a gcc.Tree (None for the default and for single-valued case labels)")
            add_simple_getter('target',
                              'gcc_python_make_wrapper_tree(CASE_LABEL(self->t))',
                              "The target of the case label, as a gcc.LabelDecl")

        cu.add_defn(getsettable.c_defn())
        cu.add_defn(methods.c_defn())
        pytype = PyGccWrapperTypeObject(identifier = 'gcc_%sType' % cc,
                              localname = cc,
                              tp_name = 'gcc.%s' % cc,
                              struct_name = 'PyGccTree',
                              tp_new = 'PyType_GenericNew',
                              tp_base = '&%s' % base_type,
                              tp_getset = getsettable.identifier,
                              tp_str = tp_str,
                              tp_repr = tp_repr,
                              tp_methods = methods.identifier,
                              )
        if tp_as_number:
            pytype.tp_as_number = '&%s' % tp_as_number
        cu.add_defn(pytype.c_defn())
        modinit_preinit += pytype.c_invoke_type_ready()
        modinit_postinit += pytype.c_invoke_add_to_module()
        

    cu.add_defn('\n/* Map from GCC tree codes to PyGccWrapperTypeObject* */\n')
    cu.add_defn('PyGccWrapperTypeObject *pytype_for_tree_code[] = {\n')
    for tree_type in tree_types:
        cu.add_defn('    &gcc_%sType, /* %s */\n' % (tree_type.camel_cased_string(), tree_type.SYM))
    cu.add_defn('};\n\n')

    cu.add_defn('\n/* Map from PyGccWrapperTypeObject* to GCC tree codes*/\n')
    cu.add_defn('int \n')
    cu.add_defn('gcc_python_tree_type_object_as_tree_code(PyObject *cls, enum tree_code *out)\n')
    cu.add_defn('{\n')
    for tree_type in tree_types:
        cu.add_defn('    if (cls == (PyObject*)&gcc_%sType) {\n'
                    '        *out = %s; return 0;\n'
                    '    }\n'
                    % (tree_type.camel_cased_string(),
                       tree_type.SYM))
    cu.add_defn('    return -1;\n')
    cu.add_defn('}\n')

    cu.add_defn("""
PyGccWrapperTypeObject*
gcc_python_autogenerated_tree_type_for_tree_code(enum tree_code code, int borrow_ref)
{
    PyGccWrapperTypeObject *result;

    assert(code >= 0);
    assert(code < MAX_TREE_CODES);

    result = pytype_for_tree_code[code];

    if (!borrow_ref) {
        Py_INCREF(result);
    }
    return result;
}

PyGccWrapperTypeObject*
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
