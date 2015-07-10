/*
   FIXME: copyright stuff
   FIXME: implement support for c_register_pragma_with_data,
          c_register_pragma_with_expansion,
          c_register_pragma_with_expansion_and_data
 */

#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"

#include "plugin.h"
#include <c-family/c-pragma.h> 

static unsigned char *
parse_pragma_params (cpp_reader *pfile)
{
    const cpp_token *token;
    unsigned int out = 0;
    unsigned int alloced = 120 + out;
    unsigned char *result = (unsigned char *) xmalloc (alloced);

    token = cpp_get_token (pfile);
    while (token->type != CPP_EOF && token->type != CPP_PRAGMA_EOL)
    {
        unsigned char *last;
        /* Include room for a possible space and the terminating nul.  */
        unsigned int len = cpp_token_len (token) + 2;

        if (out + len > alloced)
        {
            alloced *= 2;
            if (out + len > alloced)
                alloced = out + len;
            result = (unsigned char *) xrealloc (result, alloced);
        }

        last = cpp_spell_token (pfile, token, &result[out], 0);
        out = last - result;

        token = cpp_get_token (pfile);
        if (token->flags & PREV_WHITE)
            result[out++] = ' ';

        if (token->type == CPP_PRAGMA_EOL)
            _cpp_backup_tokens(pfile, 1);
    }

    result[out] = '\0';
    return result;
}

void handle_python_pragma(struct cpp_reader *cpp_reader, void *data) {
    PyObject *callback = NULL;
    PyObject *user_args = NULL;

    // unpack the {callback, args} tuple from the pragma registration
    PyArg_ParseTuple((PyObject*)data, "OO", &callback, &user_args);

    /* Debug code: */
    if (0) {
        printf("handle_python_pragma called\n");
        fprintf(stderr, "cpp_reader: %p\n", cpp_reader);
    }

    PyObject * pragma_args = Py_BuildValue("s", parse_pragma_params(cpp_reader));
    PyObject_CallFunctionObjArgs(callback, pragma_args, user_args, NULL);
}

PyObject*
PyGcc_CRegisterPragma(PyObject *self, PyObject *args)
{
    const char *directive_space = NULL;
    const char *directive = NULL;
    PyObject *callback = NULL;
    PyObject *user_args = NULL;
    unsigned char withExpansion = 0; 
    PyObject *packed_args = NULL;

    // parse the python tuple
    if (!PyArg_ParseTuple(args,
                          "ssOOb:c_register_pragma",
                          &directive_space,
                          &directive,
                          &callback,
                          &user_args,
                          &withExpansion)) {
        return NULL;
    }

    // pack callback and args so that they can be passed as a single argument
    // to the pragma handler
    packed_args = Py_BuildValue("OO", callback, user_args);

    // register the new callback
    if (withExpansion)
    {
        c_register_pragma_with_expansion_and_data(directive_space, directive,
            handle_python_pragma, (void*)packed_args);
    }
    else
    {
        c_register_pragma_with_data(directive_space, directive, handle_python_pragma,
            (void*)packed_args);
    }

    Py_RETURN_NONE;
}
