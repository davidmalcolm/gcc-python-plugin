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

/*
  Wrapper for GCC's (opt_pass *)
*/

PyObject *
gcc_Pass_repr(struct PyGccPass *self)
{
     return gcc_python_string_from_format("gcc.%s(name='%s')",
                                          Py_TYPE(self)->tp_name,
                                          self->pass->name);
}

static PyTypeObject *
get_type_for_pass_type(enum opt_pass_type pt)
{
    switch (pt) {
    default: assert(0);

    case GIMPLE_PASS:
	return &gcc_GimplePassType;

    case RTL_PASS:
	return &gcc_RtlPassType;

    case SIMPLE_IPA_PASS:
	return &gcc_SimpleIpaPassType;

    case IPA_PASS:
	return &gcc_IpaPassType;
    }
};


PyObject *
gcc_python_make_wrapper_pass(struct opt_pass *pass)
{
    PyTypeObject *type_obj;
    struct PyGccPass *pass_obj = NULL;

    if (NULL == pass) {
	Py_RETURN_NONE;
    }

    type_obj = get_type_for_pass_type(pass->type);

    pass_obj = PyObject_New(struct PyGccPass, type_obj);
    if (!pass_obj) {
        goto error;
    }

    pass_obj->pass = pass;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)pass_obj;
      
error:
    return NULL;
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
