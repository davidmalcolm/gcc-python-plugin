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

#include "diagnostic.h"

/*
  I initially attempted to directly wrap gcc's:
    diagnostic_report_diagnostic()
  given that that seems to be the abstraction within gcc/diagnostic.h: all
  instances of (struct diagnostic_info) within the gcc source tree seem to
  be allocated on the stack, within functions exposed in gcc/diagnostic.h

  However, diagnostic_report_diagnostic() ultimately calls into the
  pretty-printing routines, trying to format varargs, which doesn't make much
  sense for us: we have first-class string objects and string formatting at
  the python level.

  Thus we instead just wrap "error_at" and its analogs
*/

PyObject*
gcc_python_permerror(PyObject *self, PyObject *args)
{
    PyGccLocation *loc_obj = NULL;
    const char *msgid = NULL;
    PyObject *result_obj = NULL;
    bool result_b;

    if (!PyArg_ParseTuple(args,
			  "O!"
			  "s"
			  ":permerror",
			  &gcc_LocationType, &loc_obj,
			  &msgid)) {
        return NULL;
    }

    /* Invoke the GCC function: */
    result_b = permerror(loc_obj->loc, "%s", msgid);

    result_obj = PyBool_FromLong(result_b);

    return result_obj;
}

PyObject *
gcc_python_error(PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyGccLocation *loc_obj;
    const char *msg;
    char *keywords[] = {"location",
                        "message",
                        NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "O!s:error", keywords,
                                     &gcc_LocationType, &loc_obj,
                                     &msg)) {
        return NULL;
    }

    error_at(loc_obj->loc, "%s", msg);

    Py_RETURN_NONE;
}

PyObject *
gcc_python_warning(PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyGccLocation *loc_obj;
    const char *msg;
    PyObject *opt_obj = &_Py_NoneStruct;
    int opt_code;
    char *keywords[] = {"location",
                        "message",
                        "option",
                        NULL};
    bool was_reported;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "O!s|O:warning", keywords,

                                     /* code "O!": */
                                     &gcc_LocationType, &loc_obj,
                                     /* code: "s": */
                                     &msg,

                                     /* optional args: */
                                     /* code: "O": */
                                     &opt_obj)) {
        return NULL;
    }

    assert(opt_obj);

    /* If a gcc.Option was given, extract the code: */
    if (Py_TYPE(opt_obj) == (PyTypeObject*)&gcc_OptionType) {
        opt_code = ((PyGccOption*)opt_obj)->opt_code;

        /* Ugly workaround; see this function: */
        if (0 == gcc_python_option_is_enabled(opt_code)) {
            return PyBool_FromLong(0);
        }

    } else {
        if (opt_obj == &_Py_NoneStruct) {
            /* No gcc.Option given: an unconditionally enabled warning: */
            opt_code = 0;
        } else {
            /* Some other object was given: */
            return PyErr_Format(PyExc_TypeError,
                                ("option must be either None,"
                                 " or of type gcc.Option"));
        }
    }

    was_reported = warning_at(loc_obj->loc, opt_code, "%s", msg);

    return PyBool_FromLong(was_reported);
}

PyObject *
gcc_python_inform(PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyGccLocation *loc_obj;
    const char *msg;
    char *keywords[] = {"location",
                        "message",
                        NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "O!s:inform", keywords,
                                     &gcc_LocationType, &loc_obj,
                                     &msg)) {
        return NULL;
    }

    inform(loc_obj->loc, "%s", msg);

    Py_RETURN_NONE;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
