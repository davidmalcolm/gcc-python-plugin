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
    if ('\n' == ppobj->buf[len - 1]) {
	return gcc_python_string_from_string_and_size(ppobj->buf,
						      len - 1);
    } else {
	return gcc_python_string_from_string(ppobj->buf);
    }
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
indent-tabs-mode: nil
End:
*/
