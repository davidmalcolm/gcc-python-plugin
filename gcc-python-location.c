/*
   Copyright 2011-2013, 2017 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011-2013, 2017 Red Hat, Inc.

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
#include "gcc-c-api/gcc-location.h"

/*
  Wrapper for GCC's "location_t"

  GCC's input.h has: 
    typedef source_location location_t;

  GCC's line-map.h has:
      A logical line/column number, i.e. an "index" into a line_map:
          typedef unsigned int source_location;
*/

int
PyGccLocation_init(PyGccLocation *self, PyObject *args, PyObject *kwargs)
{
    const char *keywords[] = {"caret", "start", "finish",
                              NULL};
    PyGccLocation *caret_obj;
    PyGccLocation *start_obj;
    PyGccLocation *finish_obj;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "O!O!O!", (char**)keywords,
                                     &PyGccLocation_TypeObj, &caret_obj,
                                     &PyGccLocation_TypeObj, &start_obj,
                                     &PyGccLocation_TypeObj, &finish_obj)) {
        return -1;
    }

    self->loc
        = gcc_private_make_location (make_location (caret_obj->loc.inner,
                                                    start_obj->loc.inner,
                                                    finish_obj->loc.inner));

    return 0;
}

PyObject *
PyGccLocation_repr(struct PyGccLocation * self)
{
     return PyGccString_FromFormat("gcc.Location(file='%s', line=%i)",
                                   gcc_location_get_filename(self->loc),
                                   gcc_location_get_line(self->loc));
}

PyObject *
PyGccLocation_str(struct PyGccLocation * self)
{
     return PyGccString_FromFormat("%s:%i",
                                   gcc_location_get_filename(self->loc),
                                   gcc_location_get_line(self->loc));
}

PyObject *
PyGccLocation_richcompare(PyObject *o1, PyObject *o2, int op)
{
    struct PyGccLocation *locobj1;
    struct PyGccLocation *locobj2;
    int cond;
    PyObject *result_obj;
    const char *file1;
    const char *file2;

    if (Py_TYPE(o1) != (PyTypeObject*)&PyGccLocation_TypeObj) {
	result_obj = Py_NotImplemented;
	goto out;
    }

    if (Py_TYPE(o2) != (PyTypeObject*)&PyGccLocation_TypeObj) {
	result_obj = Py_NotImplemented;
	goto out;
    }

    locobj1 = (struct PyGccLocation *)o1;
    locobj2 = (struct PyGccLocation *)o2;

    /* First compare by filename, then by line, then by column */
    file1 = gcc_location_get_filename(locobj1->loc);
    file2 = gcc_location_get_filename(locobj2->loc);

    if (file1 != file2) {
        /* Compare by file: */
        switch (op) {
        case Py_LT:
        case Py_LE:
            /* we merge the LT and LE cases since we've already
               established that the values are not equal */
            cond = (strcmp(file1, file2) < 0);
            break;
        case Py_GT:
        case Py_GE:
            cond = (strcmp(file1, file2) > 0);
            break;
        case Py_EQ:
            cond = 0;
            break;
        case Py_NE:
            cond = 1;
            break;
        default:
            result_obj = Py_NotImplemented;
            goto out;
        }
    } else {
        /* File equality; compare by line: */
        int line1 = gcc_location_get_line(locobj1->loc);
        int line2 = gcc_location_get_line(locobj2->loc);

        if (line1 != line2) {
            switch (op) {
            case Py_LT:
            case Py_LE:
                cond = (line1 < line2);
                break;
            case Py_GT:
            case Py_GE:
                cond = (line1 > line2);
                break;
            case Py_EQ:
                cond = 0;
                break;
            case Py_NE:
                cond = 1;
                break;
            default:
                result_obj = Py_NotImplemented;
                goto out;
            }
        } else {
            /* File and line equality; compare by column: */
            int col1 = gcc_location_get_column(locobj1->loc);
            int col2 = gcc_location_get_column(locobj2->loc);

            switch (op) {
            case Py_LT:
            case Py_LE:
                cond = (col1 < col2);
                break;
            case Py_GT:
            case Py_GE:
                cond = (col1 > col2);
                break;
            case Py_EQ:
                cond = (col1 == col2);
                break;
            case Py_NE:
                cond = (col1 != col2);
                break;
            default:
                result_obj = Py_NotImplemented;
                goto out;
            }
        }
    }

    result_obj = cond ? Py_True : Py_False;

 out:
    Py_INCREF(result_obj);
    return result_obj;
}

long
PyGccLocation_hash(struct PyGccLocation * self)
{
    return self->loc.inner;
}

PyObject *
PyGccLocation_offset_column(PyGccLocation *self, PyObject *args)
{
    int offset;

    if (!PyArg_ParseTuple(args, "i", &offset)) {
        return NULL;
    }

    return PyGccLocation_New(gcc_location_offset_column(self->loc, offset));
}

PyObject *
PyGccLocation_New(gcc_location loc)
{
    struct PyGccLocation *location_obj = NULL;

    if (gcc_location_is_unknown(loc)) {
	Py_RETURN_NONE;
    }
  
    location_obj = PyGccWrapper_New(struct PyGccLocation,
                                    &PyGccLocation_TypeObj);
    if (!location_obj) {
        goto error;
    }

    location_obj->loc = loc;

    return (PyObject*)location_obj;
      
error:
    return NULL;
}

void
PyGcc_WrtpMarkForPyGccLocation(PyGccLocation *wrapper)
{
    /* empty */
}

/* rich_location. */

PyObject *
PyGccRichLocation_add_fixit_replace(PyGccRichLocation *self, PyObject *args,
                                    PyObject *kwargs)
{
    const char *keywords[] = {"new_content",
                              NULL};
    const char *new_content;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "s", (char**)keywords,
                                     &new_content)) {
        return NULL;
    }

    self->richloc.add_fixit_replace (new_content);

    Py_RETURN_NONE;
}

int
PyGccRichLocation_init(PyGccRichLocation *self, PyObject *args,
                       PyObject *kwargs)
{
    const char *keywords[] = {"location",
                              NULL};
    PyGccLocation *loc_obj;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "O!", (char**)keywords,
                                     &PyGccLocation_TypeObj, &loc_obj)) {
        return -1;
    }
    // FIXME: also need a manual dtor call
    new (&self->richloc) rich_location (line_table, loc_obj->loc.inner);
    return 0;
}

void
PyGcc_WrtpMarkForPyGccRichLocation(PyGccRichLocation *wrapper)
{
    /* empty */
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
