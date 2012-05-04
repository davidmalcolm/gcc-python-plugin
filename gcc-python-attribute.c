/*
   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011 Red Hat, Inc.

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

#include "tree.h"
#include "diagnostic.h"
#include "plugin.h"

/*
  Attribute handling
*/
/* Dictionary mapping string attribute names to callables */
static PyObject *attribute_dict;

/*
  Helper function when a custom attribute is encountered, for generating
  the arguments to the Python callback.

  The args to the function call will be the node, plus the args of the
  attribute:
    (node, arg0, arg1, ...)
*/
PyObject *
make_args_for_attribute_callback(tree node, tree args)
{
    PyObject *list_args = NULL;
    PyObject *py_args = NULL;
    PyObject *py_node = NULL;
    Py_ssize_t i;

    /* Walk "args" (a tree_list), converting to a python list of wrappers */
    list_args = gcc_python_tree_make_list_from_tree_list_chain(args);
    if (!list_args) {
        goto error;
    }

    py_args = PyTuple_New(1 + PyList_Size(list_args));
    if (!py_args) {
        goto error;
    }

    py_node = gcc_python_make_wrapper_tree(gcc_private_make_tree(node));
    if (!py_node) {
        goto error;
    }
    PyTuple_SET_ITEM(py_args, 0, py_node);

    for (i = 0; i < PyList_Size(list_args); i++) {
        PyObject *arg = PyList_GetItem(list_args, i);
        Py_INCREF(arg);
        PyTuple_SET_ITEM(py_args, i + 1, arg);
    }
    Py_DECREF(list_args);

    return py_args;

 error:
    Py_XDECREF(list_args);
    Py_XDECREF(py_args);
    Py_XDECREF(py_node);
    return NULL;
}

static tree
handle_python_attribute(tree *node, tree name, tree args,
                        int flags, bool *no_add_attrs)
{
    PyObject *callable;

    /* Debug code: */
    if (0) {
        printf("handle_python_attribute called\n");
        fprintf(stderr, "node: ");
        debug_tree(*node); /* the site of the attribute e.g. a var_decl */

        fprintf(stderr, "name: ");
        debug_tree(name); /* an identifier_node e.g. "custom_attribute_without_args" */

        fprintf(stderr, "args: ");
        debug_tree(args);  /* if present, a tree_list, e.g. of constants */
        fprintf(stderr, "flags: %i\n", flags);
        fprintf(stderr, "and here!\n");
    }

    /*
      How do we get to the attribute?

      This code:
        const struct attribute_spec *spec = lookup_attribute_spec (name);
      suggests that attributes must have unique names, so keep a dict mapping
      strings to callables
    */
    assert(IDENTIFIER_NODE == TREE_CODE(name));
    callable = PyDict_GetItemString(attribute_dict, IDENTIFIER_POINTER(name));
    assert(callable);

    {
        PyGILState_STATE gstate;
        PyObject *py_args = NULL;
        PyObject *result = NULL;

        gstate = PyGILState_Ensure();

        /*
           The args to the function call will be the node, plus the args of the
           attribute:
        */
        py_args = make_args_for_attribute_callback(*node, args);
        if (!py_args) {
            goto cleanup;
        }
        result = PyObject_Call(callable, py_args, NULL);
        if (!result) {
            /* Treat an unhandled Python error as a compilation error: */
            error("Unhandled Python exception raised within %s attribute handler",
                  IDENTIFIER_POINTER(name));
            PyErr_PrintEx(1);
        }

        /* (the result is ignored) */

    cleanup:
        Py_XDECREF(py_args);
        Py_XDECREF(result);

        PyGILState_Release(gstate);
    }

    return NULL; // FIXME
}

PyObject*
gcc_python_register_attribute(PyObject *self, PyObject *args, PyObject *kwargs)
{
    const char *name;
    int min_length;
    int max_length;
    int decl_required;
    int type_required;
    int function_type_required;
    PyObject *callable;
    struct attribute_spec *attr;

    char *keywords[] = {"name",
                        "min_length",
                        "max_length",
                        "decl_required",
                        "type_required",
                        "function_type_required",
                        "callable",
                        NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "siiiiiO:register_attribute", keywords,
                                     &name,
                                     &min_length,
                                     &max_length,
                                     &decl_required,
                                     &type_required,
                                     &function_type_required,
                                     &callable)) {
        return NULL;
    }

    /*
      "struct attribute_spec" is declared in gcc/tree.h

      register_attribute() is called by GCC for various attrs stored in
      tables of global data e.g.:
         const struct attribute_spec lto_attribute_table[]

      Hence we must malloc the data, so that it persists for the rest of the
      lifetime of the process

      We get a "handler" callback, it gets passed the name of the attribute,
      so maybe we can map names to callables.
    */
    attr = PyMem_New(struct attribute_spec, 1);
    if (!attr) {
        return PyErr_NoMemory();
    }

    /* Clear it first, for safety: */
    memset(attr, 0, sizeof(struct attribute_spec));

    /*
       Populate "attr"

       Annoyingly, all of the fields are marked as "const" within
       struct attribute_spec, so we have to cast away the constness, leading
       to the following deeply ugly code:
    */
    *(char**)&attr->name = gcc_python_strdup(name);
    if (!attr->name) {
        PyMem_Free(attr);
        return PyErr_NoMemory();
    }
    *(int*)&attr->min_length = min_length;
    *(int*)&attr->max_length = max_length;
    *(bool*)&attr->decl_required = decl_required;
    *(bool*)&attr->type_required = type_required;
    *(bool*)&attr->function_type_required = function_type_required;
    *(tree (**) (tree *node, tree name, tree args, int flags, bool *no_add_attrs))&attr->handler = handle_python_attribute;

    /*
       Associate the user-supplied callable with the given name, so that
       handle_python_attribute knows which one to call:
    */
    if (!attribute_dict) {
        attribute_dict = PyDict_New();
        if (!attribute_dict) {
            PyMem_Free((char*)attr->name);
            PyMem_Free(attr);
            return NULL;
        }
    }
    assert(attribute_dict);

    if (-1 == PyDict_SetItemString(attribute_dict, name, callable)) {
        PyMem_Free((char*)attr->name);
        PyMem_Free(attr);
        return NULL;
    }

    /*
       OK, call into GCC to register the attribute.

       (register_attribute doesn't have a return value; failures appear
       to be fatal)
    */
    register_attribute (attr);

    Py_RETURN_NONE;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
