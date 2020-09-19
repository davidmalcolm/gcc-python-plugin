/*
   Copyright 2011, 2013 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011, 2013 Red Hat, Inc.

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
#if (GCC_VERSION >= 4009)
/* Needed for placement new */
#include <new>
#endif

PyObject*
PyGccPrettyPrinter_New(void)
{
    struct PyGccPrettyPrinter *obj;

    obj = PyObject_New(struct PyGccPrettyPrinter, &PyGccPrettyPrinter_TypeObj);
    if (!obj) {
	return NULL;
    }
    
    //printf("PyGccPrettyPrinter_New\n");

    /* Gross hack for getting at a FILE* ; rewrite using fopencookie? */
    obj->buf[0] = '\0';
    obj->file_ptr = fmemopen(obj->buf, sizeof(obj->buf), "w");

#if (GCC_VERSION >= 4009)
    /* GCC 4.9 eliminated pp_construct in favor of a C++ ctor.
       Use placement new to run it on obj->pp.  */
    new ((void*)&obj->pp)
        pretty_printer(
# if (GCC_VERSION < 8003)
                       /* GCC 9 eliminated the "prefix" param.  */
                       NULL,
# endif
                       0);
#else
    pp_construct(&obj->pp, /* prefix */NULL, /* line-width */0);
#endif
    pp_needs_newline(&obj->pp) = false;
    pp_translate_identifiers(&obj->pp) = false;

    /* Connect the pp to the (FILE*): */
    obj->pp.buffer->stream = obj->file_ptr;

    //printf("PyGccPrettyPrinter_New returning: %p\n", obj);
    
    return (PyObject*)obj;
}

pretty_printer*
PyGccPrettyPrinter_as_pp(PyObject *obj)
{
    struct PyGccPrettyPrinter *ppobj;

    /* FIXME: */
    assert(Py_TYPE(obj) == &PyGccPrettyPrinter_TypeObj);
    ppobj = (struct PyGccPrettyPrinter *)obj;

    return &ppobj->pp;
}

PyObject*
PyGccPrettyPrinter_as_string(PyObject *obj)
{
    struct PyGccPrettyPrinter *ppobj;
    int len;

    /* FIXME: */
    assert(Py_TYPE(obj) == &PyGccPrettyPrinter_TypeObj);
    ppobj = (struct PyGccPrettyPrinter *)obj;

    /* Flush the pp first.  This forcibly adds a trailing newline: */
#if (GCC_VERSION < 5003)
    pp_flush(&ppobj->pp);
#else
    /*
     * pp_newline_and_flush provides the same functionality on GCC 5.3
     * and later
     */
    pp_newline_and_flush(&ppobj->pp);
#endif

    /* Convert to a python string, leaving off the trailing newline: */
    len = strlen(ppobj->buf);
    assert(len > 0);
    if ('\n' == ppobj->buf[len - 1]) {
	return PyGccString_FromString_and_size(ppobj->buf,
						      len - 1);
    } else {
	return PyGccString_FromString(ppobj->buf);
    }
}

void
PyGccPrettyPrinter_dealloc(PyObject *obj)
{
    struct PyGccPrettyPrinter *ppobj;

    /* FIXME: */
    assert(Py_TYPE(obj) == &PyGccPrettyPrinter_TypeObj);
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
