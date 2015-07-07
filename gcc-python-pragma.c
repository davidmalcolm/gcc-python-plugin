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

unsigned char *
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
    PyObject * callback = (PyObject*)data;


    /* Debug code: */
    if (0) {
        printf("handle_python_pragma called\n");
        fprintf(stderr, "cpp_reader: %p\n", cpp_reader);
    }

    
    const unsigned char * thing = parse_pragma_params(cpp_reader);
    printf("%s\n", thing);
    PyObject * args = Py_BuildValue("s", thing);
    PyObject_CallObject(callback, args);
}

PyObject*
PyGcc_CRegisterPragma(PyObject *self, PyObject *args)
{
    const char *directive_space = NULL;
    const char *directive = NULL;
    PyObject *callback = NULL;

    if (!PyArg_ParseTuple(args,
                          "ssO:c_register_pragma",
                          &directive_space,
                          &directive,
                          &callback)) {
        return NULL;
    }

    c_register_pragma_with_data(directive_space, directive, handle_python_pragma, (void*)callback);

    Py_RETURN_NONE;
}
