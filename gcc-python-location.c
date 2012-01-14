/*
   Copyright 2011, 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011, 2012 Red Hat, Inc.

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

/*
  Wrapper for GCC's "location_t"

  GCC's input.h has: 
    typedef source_location location_t;

  GCC's line-map.h has:
      A logical line/column number, i.e. an "index" into a line_map:
          typedef unsigned int source_location;
*/

PyObject *
gcc_Location_repr(struct PyGccLocation * self)
{
     return gcc_python_string_from_format("gcc.Location(file='%s', line=%i)",
                                          LOCATION_FILE(self->loc),
                                          LOCATION_LINE(self->loc));
}

PyObject *
gcc_Location_str(struct PyGccLocation * self)
{
     return gcc_python_string_from_format("%s:%i",
                                          LOCATION_FILE(self->loc),
                                          LOCATION_LINE(self->loc));
}

PyObject *
gcc_Location_richcompare(PyObject *o1, PyObject *o2, int op)
{
    struct PyGccLocation *locobj1;
    struct PyGccLocation *locobj2;
    int cond;
    PyObject *result_obj;

    assert(Py_TYPE(o1) == (PyTypeObject*)&gcc_LocationType);
    
    if (Py_TYPE(o1) != (PyTypeObject*)&gcc_LocationType) {
	result_obj = Py_NotImplemented;
	goto out;
    }

    locobj1 = (struct PyGccLocation *)o1;
    locobj2 = (struct PyGccLocation *)o2;

    switch (op) {
    case Py_EQ:
	cond = (locobj1->loc == locobj2->loc);
	break;

    case Py_NE:
	cond = (locobj1->loc != locobj2->loc);
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
gcc_python_make_wrapper_location(location_t loc)
{
    struct PyGccLocation *location_obj = NULL;

    if (UNKNOWN_LOCATION == loc) {
	Py_RETURN_NONE;
    }
  
    location_obj = PyGccWrapper_New(struct PyGccLocation, &gcc_LocationType);
    if (!location_obj) {
        goto error;
    }

    location_obj->loc = loc;

    return (PyObject*)location_obj;
      
error:
    return NULL;
}

void
wrtp_mark_for_PyGccLocation(PyGccLocation *wrapper)
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
