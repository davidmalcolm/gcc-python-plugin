/*
   Copyright 2011-2015 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011-2015 Red Hat, Inc.

   This is free software: you can redistribute it and/or modify it
   under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see
   <http://www.gnu.org/licenses/>.
*/

#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"
#include "gcc-python-compat.h"
#include "cp/cp-tree.h"
#include "gimple.h"

#include "cp/cp-tree.h" /* for TFF_* for use by PyGccFunctionDecl_get_fullname */

/* for op_symbol_code */
/* Moved to tree-pretty-print.h in gcc 4.9: */
#if (GCC_VERSION >= 4009)
#include "tree-pretty-print.h"
#else
#include "tree-flow.h"
#endif

/* "maybe_get_identifier" was moved from tree.h to stringpool.h in 4.9 */
#if (GCC_VERSION >= 4009)
#include "stringpool.h" /* for maybe_get_identifier */
#endif

#include "gcc-c-api/gcc-tree.h"
#include "gcc-c-api/gcc-type.h"
#include "gcc-c-api/gcc-private-compat.h" /* for now */

extern PyGccWrapperTypeObject PyGccIntegerCst_TypeObj;

__typeof__ (lang_check_failed) lang_check_failed __attribute__ ((weak));


/*
  Unfortunately, decl_as_string() is only available from the C++
  frontend: cc1plus (it's defined in gcc/cp/error.c).

  See http://gcc.gnu.org/ml/gcc/2011-11/msg00504.html

  Hence we redeclare the symbol as weak, and then check its definition
  against 0 before using it.
*/

__typeof__ (decl_as_string) decl_as_string __attribute__ ((weak));

/* Similar for namespace_binding, though gcc 8's r247654 (aka
   f906dcc33dd818b71e16c88cef38f33c161070db) replaced it with
   get_namespace_value and reversed the order of the params
   and r247745 (aka 9d79db401edbb9665cde47ddea2702671c89e548)
   renamed it from get_namespace_value to get_namespace_binding.  */
#if (GCC_VERSION >= 8000)
__typeof__ (get_namespace_binding) get_namespace_binding __attribute__ ((weak));
#else
__typeof__ (namespace_binding) namespace_binding __attribute__ ((weak));
#endif

/* And for cp_namespace_decls: */
__typeof__ (cp_namespace_decls) cp_namespace_decls __attribute__ ((weak));

static PyObject *
raise_cplusplus_only(const char *what)
{
    return PyErr_Format(PyExc_RuntimeError,
                        "%s is only available when compiling C++ code",
                        what);
}

static PyObject *
raise_not_during_lto(const char *what)
{
    return PyErr_Format(PyExc_RuntimeError,
                        "%s is not available during link-time optimization",
                        what);
}

//#include "rtl.h"
/*
  "struct rtx_def" is declarted within rtl.h, c.f:
    struct GTY((chain_next ("RTX_NEXT (&%h)"),
	    chain_prev ("RTX_PREV (&%h)"), variable_size)) rtx_def {
           ... snip ...
    }
    
  and seems to be the fundamental instruction type
    
  Seems to use RTX_NEXT() and RTX_PREV()
*/

/*
    Code for various tree types
 */
static PyObject *
do_pretty_print(struct PyGccTree * self, int spc, dump_flags_t flags)
{
    PyObject *ppobj = PyGccPrettyPrinter_New();
    PyObject *result = NULL;
    if (!ppobj) {
	return NULL;
    }

    dump_generic_node (PyGccPrettyPrinter_as_pp(ppobj),
		       self->t.inner, spc, flags, 0);
    result = PyGccPrettyPrinter_as_string(ppobj);
    if (!result) {
	goto error;
    }
    
    Py_XDECREF(ppobj);
    return result;
    
 error:
    Py_XDECREF(ppobj);
    return NULL;
}

PyObject *
PyGccBlock_New(gcc_block t)
{
    return PyGccTree_New(gcc_block_as_gcc_tree(t));
}

PyObject *
PyGccPointerType_New(gcc_pointer_type t)
{
    return PyGccTree_New(gcc_pointer_type_as_gcc_tree(t));
}

PyObject *
PyGccPointerType_repr(struct PyGccTree * self)
{
    PyObject *repr_name = NULL;
    PyObject *result = NULL;

    repr_name = PyGcc_GetReprOfAttribute((PyObject*)self, "dereference");
    if (!repr_name) {
        goto error;
    }

    result = PyGccString_FromFormat("%s(dereference=%s)",
                                    Py_TYPE(self)->tp_name,
                                    PyGccString_AsString(repr_name));

 error:
    Py_XDECREF(repr_name);

    return result;
}


PyObject *
PyGccCaseLabelExpr_New(gcc_case_label_expr t)
{
    return PyGccTree_New(gcc_case_label_expr_as_gcc_tree(t));
}

PyObject *
PyGccTree_str(struct PyGccTree * self)
{
    return do_pretty_print(self, 0, (dump_flags_t)0);
}

long
PyGccTree_hash(struct PyGccTree * self)
{
    if (Py_TYPE(self) == (PyTypeObject*)&PyGccComponentRef_TypeObj) {
        return (long)TREE_OPERAND(self->t.inner, 0) ^ (long)TREE_OPERAND(self->t.inner, 1);
    }

    if (Py_TYPE(self) == (PyTypeObject*)&PyGccIntegerCst_TypeObj) {
        /* Ensure that hash(cst) == hash(int(cst)) */
        PyObject *constant = PyGccIntegerConstant_get_constant(self, NULL);
        long result;
        if (!constant) {
            return -1;
        }
        result = PyObject_Hash(constant);
        Py_DECREF(constant);
        return result;
    }

    /* Use the ptr as the hash value: */
    return (long)self->t.inner;
}


PyObject *
PyGccTree_richcompare(PyObject *o1, PyObject *o2, int op)
{
    struct PyGccTree *treeobj1;
    struct PyGccTree *treeobj2;
    int cond;
    PyObject *result_obj;

    /* Specialcases: */
    if (Py_TYPE(o1) == (PyTypeObject*)&PyGccIntegerCst_TypeObj) {
        o1 = PyGccIntegerConstant_get_constant((struct PyGccTree *)o1, NULL);
        if (!o1) { return NULL; }
        result_obj = PyObject_RichCompare(o1, o2, op);
        Py_DECREF(o1);
        return result_obj;
    }
    if (Py_TYPE(o2) == (PyTypeObject*)&PyGccIntegerCst_TypeObj) {
        o2 = PyGccIntegerConstant_get_constant((struct PyGccTree *)o2, NULL);
        if (!o2) { return NULL; }
        result_obj = PyObject_RichCompare(o1, o2, op);
        Py_DECREF(o2);
        return result_obj;
    }

    if (!PyObject_TypeCheck(o1, (PyTypeObject*)&PyGccTree_TypeObj)) {
	result_obj = Py_NotImplemented;
	goto out;
    }
    if (!PyObject_TypeCheck(o2, (PyTypeObject*)&PyGccTree_TypeObj)) {
	result_obj = Py_NotImplemented;
	goto out;
    }

    treeobj1 = (struct PyGccTree *)o1;
    treeobj2 = (struct PyGccTree *)o2;

    if (Py_TYPE(o1) == (PyTypeObject*)&PyGccComponentRef_TypeObj) {
        if (Py_TYPE(o2) == (PyTypeObject*)&PyGccComponentRef_TypeObj) {
            switch (op) {
            case Py_EQ:
                cond = ((TREE_OPERAND(treeobj1->t.inner, 0) == TREE_OPERAND(treeobj2->t.inner, 0)) &&
                        (TREE_OPERAND(treeobj1->t.inner, 1) == TREE_OPERAND(treeobj2->t.inner, 1)));
                break;

            case Py_NE:
                cond = !((TREE_OPERAND(treeobj1->t.inner, 0) == TREE_OPERAND(treeobj2->t.inner, 0)) &&
                         (TREE_OPERAND(treeobj1->t.inner, 1) == TREE_OPERAND(treeobj2->t.inner, 1)));
                break;

            default:
                result_obj = Py_NotImplemented;
                goto out;
            }
            result_obj = cond ? Py_True : Py_False;
            goto out;
        }
    }

    switch (op) {
    case Py_EQ:
	cond = (treeobj1->t.inner == treeobj2->t.inner);
	break;

    case Py_NE:
	cond = (treeobj1->t.inner != treeobj2->t.inner);
	break;

    default:
        result_obj = Py_NotImplemented;
        goto out;
    }
    result_obj = cond ? Py_True : Py_False;

 out:
    Py_INCREF(result_obj);
    return result_obj;
}

PyObject *
PyGccTree_get_str_no_uid(struct PyGccTree *self, void *closure)
{
    return do_pretty_print(self, 0, TDF_NOUID);
}

PyObject *
PyGccTree_get_symbol(PyObject *cls, PyObject *args)
{
    enum tree_code code;

    if (-1 == PyGcc_tree_type_object_as_tree_code(cls, &code)) {
        PyErr_SetString(PyExc_TypeError,
                        "no symbol associated with this type");
        return NULL;
    }

    return PyGccString_FromString(op_symbol_code(code));
}

PyObject *
PyGccDeclaration_repr(struct PyGccTree * self)
{
    PyObject *name = NULL;
    PyObject *result = NULL;

    if (DECL_NAME(self->t.inner)) {
	name = PyGccDeclaration_get_name(self, NULL);
	if (!name) {
	    goto error;
	}

        result = PyGccString_FromFormat("%s('%s')",
                                               Py_TYPE(self)->tp_name,
                                               PyGccString_AsString(name));
	Py_DECREF(name);
    } else {
        result = PyGccString_FromFormat("%s(%u)",
				     Py_TYPE(self)->tp_name,
				     DECL_UID (self->t.inner));
    }

    return result;
error:
    Py_XDECREF(name);
    Py_XDECREF(result);
    return NULL;
}

PyObject *
PyGccFunctionDecl_get_fullname(struct PyGccTree *self, void *closure)
{
    const char *str;

    if (NULL == decl_as_string) {
        return raise_cplusplus_only("attribute 'fullname'");
    }

    str = decl_as_string(self->t.inner,
                         TFF_DECL_SPECIFIERS
                         |TFF_RETURN_TYPE
                         |TFF_FUNCTION_DEFAULT_ARGUMENTS
                         |TFF_EXCEPTION_SPECIFICATION);
    return PyGccString_FromString(str);
}

PyObject *
PyGccFunctionDecl_get_callgraph_node(struct PyGccTree *self, void *closure)
{
    /* cgraph_get_node became cgraph_node::get in 5.0 */
    struct cgraph_node *node;
#if (GCC_VERSION >= 5000)
    node = cgraph_node::get(self->t.inner);
#else
    node = cgraph_get_node(self->t.inner);
#endif
    return PyGccCallgraphNode_New(gcc_private_make_cgraph_node(node));
}

PyObject *
PyGccArrayRef_repr(PyObject *self)
{
    PyObject *array_repr = NULL;
    PyObject *index_repr = NULL;
    PyObject *result = NULL;

    array_repr = PyGcc_GetReprOfAttribute(self, "array");
    if (!array_repr) {
        goto error;
    }
    index_repr =PyGcc_GetReprOfAttribute(self, "index");
    if (!index_repr) {
        goto error;
    }

    result = PyGccString_FromFormat("%s(array=%s, index=%s)",
                                           Py_TYPE(self)->tp_name,
                                           PyGccString_AsString(array_repr),
                                           PyGccString_AsString(index_repr));

 error:
    Py_XDECREF(array_repr);
    Py_XDECREF(index_repr);

    return result;
}

PyObject *
PyGccComponentRef_repr(PyObject *self)
{
    PyObject *target_repr = NULL;
    PyObject *field_repr = NULL;
    PyObject *result = NULL;

    target_repr = PyGcc_GetReprOfAttribute(self, "target");
    if (!target_repr) {
        goto error;
    }
    field_repr = PyGcc_GetReprOfAttribute(self, "field");
    if (!field_repr) {
        goto error;
    }

    result = PyGccString_FromFormat("%s(target=%s, field=%s)",
                                           Py_TYPE(self)->tp_name,
                                           PyGccString_AsString(target_repr),
                                           PyGccString_AsString(field_repr));

 error:
    Py_XDECREF(target_repr);
    Py_XDECREF(field_repr);

    return result;
}

PyObject *
PyGccIdentifierNode_repr(struct PyGccTree * self)
{
    if (IDENTIFIER_POINTER(self->t.inner)) {
        return PyGccString_FromFormat("%s(name='%s')",
                                             Py_TYPE(self)->tp_name,
                                             IDENTIFIER_POINTER(self->t.inner));
    } else {
        return PyGccString_FromFormat("%s(name=None)",
                                             Py_TYPE(self)->tp_name);
    }
}

PyObject *
PyGccType_get_attributes(struct PyGccTree *self, void *closure)
{
    /* gcc/tree.h defines TYPE_ATTRIBUTES(NODE) as:
       "A TREE_LIST of IDENTIFIER nodes of the attributes that apply
       to this type"

       Looking at:
          typedef int (example3)(const char *, const char *, const char *)
              __attribute__((nonnull(1)))
              __attribute__((nonnull(3)));
       (which is erroneous), we get this for TYPE_ATTRIBUTES:
         gcc.TreeList(purpose=gcc.IdentifierNode(name='nonnull'),
                      value=gcc.TreeList(purpose=None,
                                         value=gcc.IntegerCst(3),
                                         chain=None),
                      chain=gcc.TreeList(purpose=gcc.IdentifierNode(name='nonnull'),
                                         value=gcc.TreeList(purpose=None,
                                                            value=gcc.IntegerCst(1),
                                                            chain=None),
                                         chain=None)
                      )
    */
    tree attr;
    PyObject *result = PyDict_New();
    if (!result) {
        return NULL;
    }
    for (attr = TYPE_ATTRIBUTES(self->t.inner); attr; attr = TREE_CHAIN(attr)) {
        const char *attrname = IDENTIFIER_POINTER(TREE_PURPOSE(attr));
        PyObject *values;
        values = PyGcc_TreeMakeListFromTreeList(TREE_VALUE(attr));
        if (!values) {
            goto error;
        }

        if (-1 == PyDict_SetItemString(result, attrname, values)) {
            Py_DECREF(values);
            goto error;
        }
        Py_DECREF(values);
    }

    return result;

 error:
    Py_DECREF(result);
    return NULL;
}

/*
  Weakly import c_sizeof_or_alignof_type; it's not available in lto1
  (link-time optimization)
*/
__typeof__ (c_sizeof_or_alignof_type) c_sizeof_or_alignof_type __attribute__ ((weak));

PyObject *
PyGccType_get_sizeof(struct PyGccTree *self, void *closure)
{
    if (NULL == c_sizeof_or_alignof_type) {
        return raise_not_during_lto("Type.sizeof");
    }

    /*
      c_sizeof_or_alignof_type wants a location; we use a fake one
    */
    tree t_sizeof = c_sizeof_or_alignof_type(input_location, self->t.inner, true,
#if (GCC_VERSION >= 4009)
                                             false,
#endif
                                             0);
    PyObject *str;

    /* This gives us either an INTEGER_CST or the dummy error type: */
    if (INTEGER_CST == TREE_CODE(t_sizeof)) {
        return PyGcc_int_from_int_cst (t_sizeof);
    }

    /* Error handling: */
    str = PyGccTree_str(self);
    if (str) {
        PyErr_Format(PyExc_TypeError,
                     "type \"%s\" does not have a \"sizeof\"",
                     PyGccString_AsString(str));
        Py_DECREF(str);
    } else {
        PyErr_Format(PyExc_TypeError,
                     "type does not have a \"sizeof\"");
    }
    return NULL;
}

__typeof__ (c_common_signed_type) c_common_signed_type __attribute__ ((weak));

PyObject *
PyGccIntegerType_get_signed_equivalent(struct PyGccTree * self, void *closure)
{
    if (NULL == c_common_signed_type)
        return raise_not_during_lto("gcc.IntegerType.signed_equivalent");

    return PyGccTree_New(gcc_private_make_tree(c_common_signed_type(self->t.inner)));
}

__typeof__ (c_common_unsigned_type) c_common_unsigned_type __attribute__ ((weak));

PyObject *
PyGccIntegerType_get_unsigned_equivalent(struct PyGccTree * self, void *closure)
{
    if (NULL == c_common_unsigned_type)
        return raise_not_during_lto("gcc.IntegerType.unsigned_equivalent");

    return PyGccTree_New(gcc_private_make_tree(c_common_unsigned_type(self->t.inner)));
}

PyObject *
PyGccIntegerType_repr(struct PyGccTree * self)
{
    PyObject *repr_name = NULL;
    PyObject *result = NULL;

    repr_name = PyGcc_GetReprOfAttribute((PyObject*)self, "name");
    if (!repr_name) {
        goto error;
    }

    result = PyGccString_FromFormat("%s(name=%s)",
                                    Py_TYPE(self)->tp_name,
                                    PyGccString_AsString(repr_name));

 error:
    Py_XDECREF(repr_name);

    return result;
}

PyObject *
PyGccFunction_TypeObj_get_argument_types(struct PyGccTree * self, void *closure)
{
    PyObject *result;
    PyObject *item;
    int i, size;
    tree iter;
    tree head = TYPE_ARG_TYPES(self->t.inner);

    /* Get length of chain */
    for (size = 0, iter = head;
         iter && iter != error_mark_node && iter != void_list_node;
         iter = TREE_CHAIN(iter), size++) {
        /* empty */
    }

    /* "size" should now be the length of the chain */

    result = PyTuple_New(size);
    if (!result) {
        return NULL;
    }

    for (i = 0, iter = head; i < size; iter = TREE_CHAIN(iter), i++) {
	item = PyGccTree_New(gcc_private_make_tree(TREE_VALUE(iter)));
	if (!item) {
	    goto error;
	}
        if (0 != PyTuple_SetItem(result, i, item)) {
            Py_DECREF(item);
            goto error;
        }
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

PyObject *
PyGccFunction_TypeObj_is_variadic(struct PyGccTree * self, void *closure)
{
    tree iter;
    tree head = TYPE_ARG_TYPES(self->t.inner);

    /* Get length of chain */
    for (iter = head;
         iter && iter != error_mark_node && iter != void_list_node;
         iter = TREE_CHAIN(iter)) {
        /* empty */
    }

    if (iter == void_list_node)
        Py_RETURN_FALSE;
    Py_RETURN_TRUE;
}

PyObject *
PyGccMethodType_get_argument_types(struct PyGccTree * self,void *closure)
{
    return PyGccFunction_TypeObj_get_argument_types(self, closure);
}

PyObject *
PyGccMethodType_is_variadic(struct PyGccTree * self,void *closure)
{
    return PyGccFunction_TypeObj_is_variadic(self, closure);
}

PyObject *
PyGccConstructor_get_elements(PyObject *self, void *closure)
{
    struct PyGccTree * self_as_tree;
    PyObject *result = NULL;
    tree node;
    unsigned HOST_WIDE_INT cnt;
    tree index, value;

    self_as_tree = (struct PyGccTree *)self; /* FIXME */
    node = self_as_tree->t.inner;

    result = PyList_New(GCC_COMPAT_VEC_LENGTH(constructor_elt,
                                              CONSTRUCTOR_ELTS (node)));
    if (!result) {
	goto error;
    }

    FOR_EACH_CONSTRUCTOR_ELT (CONSTRUCTOR_ELTS (node),
			      cnt, index, value) {
	PyObject *obj_index = NULL;
	PyObject *obj_value = NULL;
	PyObject *obj_pair = NULL;
	obj_index = PyGccTree_New(gcc_private_make_tree(index));
	if (!obj_index) {
	    goto error;
	}
	obj_value = PyGccTree_New(gcc_private_make_tree(value));
	if (!obj_value) {
	    Py_DECREF(obj_index);
	    goto error;
	}
	obj_pair = PyTuple_Pack(2, obj_index, obj_value);
	if (!obj_pair) {
	    Py_DECREF(obj_value);
	    Py_DECREF(obj_index);
	    goto error;
	}
        Py_DECREF(obj_value);
        Py_DECREF(obj_index);

	if (-1 == PyList_SetItem(result, cnt, obj_pair)) {
	    Py_DECREF(obj_pair);
	    goto error;
	}
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

#if (GCC_VERSION >= 5000)

static void
print_integer_cst_to_buf(tree int_cst, char *buf, tree type)
{
    /*
      GCC 8 commit r253595 (aka e3d0f65c14ffd7a63455dc1aa9d0405d25b327e4,
      2017-10-10) introduces and requires the use of wi::to_wide on
      INTEGER_CST.
    */
#if (GCC_VERSION >= 8000)
    print_dec(wi::to_wide(int_cst), buf, TYPE_SIGN (type));
#else
    print_dec(int_cst, buf, TYPE_SIGN (type));
#endif
}

#endif /* #if (GCC_VERSION >= 5000) */

PyObject *
PyGcc_int_from_int_cst(tree int_cst)
{
    tree type = TREE_TYPE(int_cst);
#if (GCC_VERSION >= 5000)
    char buf[WIDE_INT_PRINT_BUFFER_SIZE];
    print_integer_cst_to_buf (int_cst, buf, type);
    return PyGcc_int_from_decimal_string_buffer(buf);
#else
    return PyGcc_int_from_double_int(TREE_INT_CST(int_cst),
                                     TYPE_UNSIGNED(type));
#endif
}

PyObject *
PyGccIntegerConstant_get_constant(struct PyGccTree * self, void *closure)
{
    return PyGcc_int_from_int_cst(self->t.inner);
}

PyObject *
PyGccIntegerConstant_repr(struct PyGccTree * self)
{
    tree type = TREE_TYPE(self->t.inner);
#if (GCC_VERSION >= 5000)
    char buf[WIDE_INT_PRINT_BUFFER_SIZE];
    print_integer_cst_to_buf (self->t.inner, buf, type);
#else
    char buf[512];
    PyGcc_DoubleIntAsText(TREE_INT_CST(self->t.inner),
                                  TYPE_UNSIGNED(type),
                                  buf, sizeof(buf));
#endif
    return PyGccString_FromFormat("%s(%s)",
                                         Py_TYPE(self)->tp_name,
                                         buf);
}

PyObject *
PyGccRealCst_get_constant(struct PyGccTree * self, void *closure)
{
    /* "cheat" and go through the string representation: */
    REAL_VALUE_TYPE *d;
    char buf[60];
    PyObject *str;
    PyObject *result;

    d = TREE_REAL_CST_PTR(self->t.inner);
    real_to_decimal (buf, d, sizeof (buf), 0, 1);

    str = PyGccString_FromString(buf);
    if (!str) {
        return NULL;
    }

    /*
      PyFloat_FromString API dropped its redundant second argument
      in Python 3
     */
#if PY_MAJOR_VERSION == 3
    result = PyFloat_FromString(str);
#else
    result = PyFloat_FromString(str, NULL);
#endif

    Py_DECREF(str);
    return result;
}

PyObject *
PyGccRealCst_repr(struct PyGccTree * self)
{
    REAL_VALUE_TYPE *d;
    char buf[60];

    d = TREE_REAL_CST_PTR(self->t.inner);
    real_to_decimal (buf, d, sizeof (buf), 0, 1);
    return PyGccString_FromFormat("%s(%s)",
                                         Py_TYPE(self)->tp_name,
                                         buf);
}

PyObject *
PyGccStringConstant_repr(struct PyGccTree * self)
{
    PyObject *str_obj;
    PyObject *result = NULL;

    str_obj = PyGccStringOrNone(TREE_STRING_POINTER(self->t.inner));
    if (!str_obj) {
        return NULL;
    }
#if PY_MAJOR_VERSION >= 3
    result = PyGccString_FromFormat("%s(%R)",
                                           Py_TYPE(self)->tp_name,
                                           str_obj);
#else
    {
        PyObject *str_repr;
        str_repr = PyObject_Repr(str_obj);
        if (!str_repr) {
            Py_DECREF(str_obj);
            return NULL;
        }
        result = PyGccString_FromFormat("%s(%s)",
                                               Py_TYPE(self)->tp_name,
                                               PyString_AsString(str_repr));
        Py_DECREF(str_repr);
    }
#endif
    Py_DECREF(str_obj);
    return result;
}

PyObject *
PyGccTypeDecl_get_pointer(struct PyGccTree *self, void *closure)
{
    tree decl_type = TREE_TYPE(self->t.inner);
    if (!decl_type) {
        PyErr_SetString(PyExc_ValueError, "gcc.TypeDecl has no associated type");
        return NULL;
    }
    return PyGccTree_New(gcc_private_make_tree(build_pointer_type(decl_type)));
}

PyObject *
PyGccSsaName_repr(struct PyGccTree * self)
{
    int version;
    PyObject *repr_var = NULL;
    PyObject *result = NULL;

    version = gcc_ssa_name_get_version(gcc_tree_as_gcc_ssa_name(self->t));
    repr_var = PyGcc_GetReprOfAttribute((PyObject*)self, "var");
    if (!repr_var) {
        goto error;
    }

    result = PyGccString_FromFormat("%s(var=%s, version=%i)",
                                           Py_TYPE(self)->tp_name,
                                           PyGccString_AsString(repr_var),
                                           version);

 error:
    Py_XDECREF(repr_var);

    return result;
}

PyObject *
PyGccTreeList_repr(struct PyGccTree * self)
{
    PyObject *purpose = NULL;
    PyObject *value = NULL;
    PyObject *chain = NULL;
    PyObject *repr_purpose = NULL;
    PyObject *repr_value = NULL;
    PyObject *repr_chain = NULL;
    PyObject *result = NULL;

    purpose = PyGccTree_New(gcc_private_make_tree(TREE_PURPOSE(self->t.inner)));
    if (!purpose) {
        goto error;
    }
    value = PyGccTree_New(gcc_private_make_tree(TREE_VALUE(self->t.inner)));
    if (!value) {
        goto error;
    }
    chain = PyGccTree_New(gcc_private_make_tree(TREE_CHAIN(self->t.inner)));
    if (!chain) {
        goto error;
    }

    repr_purpose = PyObject_Repr(purpose);
    if (!repr_purpose) {
        goto error;
    }
    repr_value = PyObject_Repr(value);
    if (!repr_value) {
        goto error;
    }
    repr_chain = PyObject_Repr(chain);
    if (!repr_chain) {
        goto error;
    }

    result = PyGccString_FromFormat("%s(purpose=%s, value=%s, chain=%s)",
                                           Py_TYPE(self)->tp_name,
                                           PyGccString_AsString(repr_purpose),
                                           PyGccString_AsString(repr_value),
                                           PyGccString_AsString(repr_chain));
 error:
    Py_XDECREF(purpose);
    Py_XDECREF(value);
    Py_XDECREF(chain);
    Py_XDECREF(repr_purpose);
    Py_XDECREF(repr_value);
    Py_XDECREF(repr_chain);

    return result;
}

PyObject *
PyGccCaseLabelExpr_repr(PyObject * self)
{
    PyObject *low_repr = NULL;
    PyObject *high_repr = NULL;
    PyObject *target_repr = NULL;
    PyObject *result = NULL;

    low_repr = PyGcc_GetReprOfAttribute(self, "low");
    if (!low_repr) {
        goto cleanup;
    }
    high_repr = PyGcc_GetReprOfAttribute(self, "high");
    if (!high_repr) {
        goto cleanup;
    }
    target_repr = PyGcc_GetReprOfAttribute(self, "target");
    if (!target_repr) {
        goto cleanup;
    }

    result = PyGccString_FromFormat("%s(low=%s, high=%s, target=%s)",
                                           Py_TYPE(self)->tp_name,
                                           PyGccString_AsString(low_repr),
                                           PyGccString_AsString(high_repr),
                                           PyGccString_AsString(target_repr));

 cleanup:
    Py_XDECREF(low_repr);
    Py_XDECREF(high_repr);
    Py_XDECREF(target_repr);
    return result;
}

PyObject *
PyGccNamespaceDecl_lookup(struct PyGccTree * self, PyObject *args, PyObject *kwargs)
{
    tree t_result;
    tree t_name;

    const char *name;
    const char *keywords[] = {"name",
                              NULL};


    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "s:lookup", (char**)keywords,
                                     &name)) {
        return NULL;
    }

#if (GCC_VERSION >= 8000)
    if (NULL == get_namespace_binding) {
#else
    if (NULL == namespace_binding) {
#endif
        return raise_cplusplus_only("gcc.NamespaceDecl.lookup");
    }

    t_name = get_identifier(name);

#if (GCC_VERSION >= 8000)
    t_result = get_namespace_binding(self->t.inner, t_name);
#else
    t_result = namespace_binding(t_name, self->t.inner);
#endif

    return PyGccTree_New(gcc_private_make_tree(t_result));
}

PyObject *
PyGccNamespaceDecl_unalias(struct PyGccTree * self, PyObject *args, PyObject *kwargs)
{
  tree t = self->t.inner;

  if (NULL == DECL_NAMESPACE_ALIAS(t)) {
    Py_INCREF(self);
    return (PyObject *)self;
  }

  while (DECL_NAMESPACE_ALIAS(t)) {
    t = DECL_NAMESPACE_ALIAS(t);
  }

  return PyGccTree_New(gcc_private_make_tree(t));
}

static PyObject *
raise_namespace_alias(const char *what)
{
    return PyErr_Format(PyExc_RuntimeError,
                        "%s is not valid for an alias",
                        what);
}

PyObject *
PyGccNamespaceDecl_declarations(tree t)
{
  if (NULL == cp_namespace_decls)
    return raise_cplusplus_only("gcc.NamespaceDecl.declarations");

  /* throw if we are an alias,
     if we unalias it, it may return a list containing itself.  */
  if (DECL_NAMESPACE_ALIAS(t))
    return raise_namespace_alias("gcc.NamespaceDecl.declarations");

  return PyGcc_TreeListFromChain(cp_namespace_decls(t));
}

#if (GCC_VERSION >= 8000)

static int is_namespace (tree decl, void *)
{
    return (TREE_CODE (decl) == NAMESPACE_DECL
            && !DECL_NAMESPACE_ALIAS (decl));
}

#endif /* #if (GCC_VERSION >= 8000) */

PyObject *
PyGccNamespaceDecl_namespaces(tree t)
{
  /* We don't actually call cp_namespace_decls, but we only actually call
     c++ specific macros, not sure what happens.  */
  if (NULL == cp_namespace_decls)
    return raise_cplusplus_only("gcc.NamespaceDecl.namespaces");

  /* throw if we are an alias,
     if we unalias it, it may return a list containing itself.  */
  if (DECL_NAMESPACE_ALIAS(t))
    return raise_namespace_alias("gcc.NamespaceDecl.namespaces");

  /* GCC 8's r248821 (aka f7564df45462679c3b0b82f2942f5fb50b640113)
     eliminated the "namespaces" field from cp_binding_level.  */

#if (GCC_VERSION >= 8000)
  return PyGcc_TreeListFromChainWithFilter(NAMESPACE_LEVEL(t)->names,
                                           is_namespace, NULL);
#else
  return PyGcc_TreeListFromChain(NAMESPACE_LEVEL(t)->namespaces);
#endif
}

/* Accessing the fields and methods of compound types.
   GCC 8's r250413 (aka ab87ee8f509c0b600102195704105d4d98ec59d9)
   eliminated TYPE_METHODS, instead putting both fields and methods
   on the TYPE_FIELDS chain, using DECL_DECLARES_FUNCTION_P to
   distinguish them.  */

#if (GCC_VERSION >= 8000)

static int is_field (tree t, void *)
{
    return !DECL_DECLARES_FUNCTION_P (t);
}

static int is_method (tree t, void *)
{
    return DECL_DECLARES_FUNCTION_P (t);
}

#endif /* #if (GCC_VERSION >= 8000) */

PyObject *
PyGcc_GetFields(struct PyGccTree *self)
{
#if (GCC_VERSION >= 8000)
    return PyGcc_TreeListFromChainWithFilter(TYPE_FIELDS(self->t.inner),
                                             is_field, NULL);
#else
    return PyGcc_TreeListFromChain(TYPE_FIELDS(self->t.inner));
#endif
}

PyObject *
PyGcc_GetMethods(struct PyGccTree *self)
{
#if (GCC_VERSION >= 8000)
    return PyGcc_TreeListFromChainWithFilter(TYPE_FIELDS(self->t.inner),
                                             is_method, NULL);
#else
    return PyGcc_TreeListFromChain(TYPE_METHODS(self->t.inner));
#endif
}

/* 
   GCC's debug_tree is implemented in:
     gcc/print-tree.c
   e.g. in:
     /usr/src/debug/gcc-4.6.0-20110321/gcc/print-tree.c
   and appears to be a good place to look when figuring out how the tree data
   works.

   dump_generic_node is defined around line 580 of tree-pretty-print.c
*/

union tree_or_ptr {
    gcc_tree tree;
    void *ptr;
};

static PyObject *
real_make_tree_wrapper(void *ptr)
{

    struct PyGccTree *tree_obj = NULL;
    PyGccWrapperTypeObject* tp;
    union tree_or_ptr u;
    u.ptr = ptr;

    if (NULL == ptr) {
	Py_RETURN_NONE;
    }
  
    tp = PyGcc_autogenerated_tree_type_for_tree(u.tree, 1);
    assert(tp);
    
    tree_obj = PyGccWrapper_New(struct PyGccTree, tp);
    if (!tree_obj) {
        goto error;
    }

    tree_obj->t = u.tree;

    return (PyObject*)tree_obj;
      
error:
    return NULL;
}

void
PyGcc_WrtpMarkForPyGccTree(PyGccTree *wrapper)
{
    gcc_tree_mark_in_use(wrapper->t);
}

/*
   Ensure we have a unique PyGccTree per tree address (by maintaining a dict)
   (what about lifetimes?)
*/
static PyObject *tree_wrapper_cache = NULL;

PyObject *
PyGccTree_New(gcc_tree t)
{
    union tree_or_ptr u;
    u.tree = t;
    return PyGcc_LazilyCreateWrapper(&tree_wrapper_cache,
					    u.ptr,
					    real_make_tree_wrapper);
}

PyObject *
PyGccTree_NewUnique(gcc_tree t)
{
    union tree_or_ptr u;
    u.tree = t;
    return real_make_tree_wrapper(u.ptr);
}

/* Walk the chain of a tree, building a python list of wrapper gcc.Tree
   instances */
PyObject *
PyGcc_TreeListFromChain(tree t)
{
    PyObject *result = NULL;
    
    result = PyList_New(0);
    if (!result) {
	goto error;
    }

    while (t) {
	PyObject *item;
	item = PyGccTree_New(gcc_private_make_tree(t));
	if (!item) {
	    goto error;
	}
	if (-1 == PyList_Append(result, item)) {
            Py_DECREF(item);
	    goto error;
	}
        Py_DECREF(item);
	t = TREE_CHAIN(t);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

/* As above, but only add nodes for which "filter" returns true.  */
PyObject *
PyGcc_TreeListFromChainWithFilter(tree t,
                                  int (*filter) (tree, void *),
                                  void *user_data)
{
    PyObject *result = NULL;

    result = PyList_New(0);
    if (!result) {
	goto error;
    }

    while (t) {
        if (filter (t, user_data)) {
            PyObject *item;

            item = PyGccTree_New(gcc_private_make_tree(t));
            if (!item) {
                goto error;
            }
            if (-1 == PyList_Append(result, item)) {
                Py_DECREF(item);
                goto error;
            }
            Py_DECREF(item);
        }

        t = TREE_CHAIN(t);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

/*
  As above, but expect nodes of the form:
     tree_list  ---> value
         +--chain--> tree_list ---> value
                         +--chain--> tree_list ---> value
                                         +---chain--> NULL
  Extract a list of objects for the values
 */
PyObject *
PyGcc_TreeMakeListFromTreeList(tree t)
{
    PyObject *result = NULL;

    result = PyList_New(0);
    if (!result) {
       goto error;
    }

    while (t) {
       PyObject *item;
       item = PyGccTree_New(gcc_private_make_tree(TREE_VALUE(t)));
       if (!item) {
           goto error;
       }
       if (-1 == PyList_Append(result, item)) {
           Py_DECREF(item);
           goto error;
       }
       Py_DECREF(item);
       t = TREE_CHAIN(t);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

/*
  As above, but expect nodes of the form:
     tree_list  ---> (purpose, value)
         +--chain--> tree_list ---> (purpose, value)
                         +--chain--> tree_list ---> (purpose, value)
                                         +---chain--> NULL
  Extract a list of objects for the values
 */
PyObject *
PyGcc_TreeMakeListOfPairsFromTreeListChain(tree t)
{
    PyObject *result = NULL;

    result = PyList_New(0);
    if (!result) {
       goto error;
    }

    while (t) {
       PyObject *purpose;
       PyObject *value;
       PyObject *pair;
       purpose = PyGccTree_New(gcc_private_make_tree(TREE_PURPOSE(t)));
       if (!purpose) {
           goto error;
       }
       value = PyGccTree_New(gcc_private_make_tree(TREE_VALUE(t)));
       if (!value) {
           Py_DECREF(purpose);
           goto error;
       }
       pair = Py_BuildValue("OO", purpose, value);
       Py_DECREF(purpose);
       Py_DECREF(value);
       if (!pair) {
           goto error;
       }
       if (-1 == PyList_Append(result, pair)) {
           Py_DECREF(pair);
           goto error;
       }
       Py_DECREF(pair);
       t = TREE_CHAIN(t);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

PyObject *
VEC_tree_as_PyList(
#if (GCC_VERSION >= 4008)
    vec<tree, va_gc> *vec_nodes
#else
    VEC(tree,gc) *vec_nodes
#endif
)
{
    PyObject *result = NULL;
    int i;
    tree t;

    result = PyList_New(GCC_COMPAT_VEC_LENGTH(tree, vec_nodes));
    if (!result) {
	goto error;
    }

    GCC_COMPAT_FOR_EACH_VEC_ELT(tree, vec_nodes, i, t) {
	PyObject *item;
	item = PyGccTree_New(gcc_private_make_tree(t));
	if (!item) {
	    goto error;
	}
	PyList_SetItem(result, i, item);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
