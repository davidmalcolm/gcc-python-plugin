#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"

PyObject*
gcc_python_pretty_printer_new(void)
{
    struct PyGccPrettyPrinter *obj;

    obj = PyObject_New(struct PyGccPrettyPrinter, &gcc_PrettyPrinterType);
    if (!obj) {
	return NULL;
    }
    
    //printf("gcc_python_pretty_printer_new\n");

    /* Gross hack for getting at a FILE* ; rewrite using fopencookie? */
    obj->buf[0] = '\0';
    obj->file_ptr = fmemopen(obj->buf, sizeof(obj->buf), "w");

    pp_construct(&obj->pp, /* prefix */NULL, /* line-width */0);
    pp_needs_newline(&obj->pp) = false;
    pp_translate_identifiers(&obj->pp) = false;

    /* Connect the pp to the (FILE*): */
    obj->pp.buffer->stream = obj->file_ptr;

    //printf("gcc_python_pretty_printer_new returning: %p\n", obj);
    
    return (PyObject*)obj;
}

pretty_printer*
gcc_python_pretty_printer_as_pp(PyObject *obj)
{
    struct PyGccPrettyPrinter *ppobj;

    /* FIXME: */
    assert(Py_TYPE(obj) == &gcc_PrettyPrinterType);
    ppobj = (struct PyGccPrettyPrinter *)obj;

    return &ppobj->pp;
}

PyObject*
gcc_python_pretty_printer_as_string(PyObject *obj)
{
    struct PyGccPrettyPrinter *ppobj;
    int len;

    /* FIXME: */
    assert(Py_TYPE(obj) == &gcc_PrettyPrinterType);
    ppobj = (struct PyGccPrettyPrinter *)obj;

    /* Flush the pp first.  This forcibly adds a trailing newline: */
    pp_flush(&ppobj->pp);

    /* Convert to a python string, leaving off the trailing newline: */
    len = strlen(ppobj->buf);
    assert(len > 0);
    assert('\n' == ppobj->buf[len - 1]);
    return PyString_FromStringAndSize(ppobj->buf,
				      len - 1);
}

void
gcc_PrettyPrinter_dealloc(PyObject *obj)
{
    struct PyGccPrettyPrinter *ppobj;

    /* FIXME: */
    assert(Py_TYPE(obj) == &gcc_PrettyPrinterType);
    ppobj = (struct PyGccPrettyPrinter *)obj;

    /* Close the (FILE*), if open: */
    if (ppobj->file_ptr) {
	fclose(ppobj->file_ptr);
	ppobj->file_ptr = NULL;
    }

    Py_TYPE(obj)->tp_free(obj);
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
End:
*/
