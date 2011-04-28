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
     return PyString_FromFormat("gcc.Location(file='%s', line=%i)",
				LOCATION_FILE(self->loc),
				LOCATION_LINE(self->loc));
}

PyObject *
gcc_Location_str(struct PyGccLocation * self)
{
     return PyString_FromFormat("%s:%i",
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

    assert(Py_TYPE(o1) == &gcc_LocationType);
    
    if (Py_TYPE(o1) != &gcc_LocationType) {
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
  
    location_obj = PyObject_New(struct PyGccLocation, &gcc_LocationType);
    if (!location_obj) {
        goto error;
    }

    location_obj->loc = loc;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)location_obj;
      
error:
    return NULL;
}


/*
  PEP-7  
Local variables:
c-basic-offset: 4
End:
*/
