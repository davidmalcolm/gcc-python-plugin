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
#include "gcc-c-api/gcc-variable.h"

PyObject *
PyGccVariable_New(gcc_variable var)
{
    struct PyGccVariable *var_obj = NULL;

    if (NULL == var.inner) {
	Py_RETURN_NONE;
    }
  
    var_obj = PyGccWrapper_New(struct PyGccVariable, &PyGccVariable_TypeObj);
    if (!var_obj) {
        goto error;
    }

    var_obj->var = var;

    return (PyObject*)var_obj;
      
error:
    return NULL;
}

void
PyGcc_WrtpMarkForPyGccVariable(PyGccVariable *wrapper)
{
    /* Mark the underlying object (recursing into its fields): */
    gcc_variable_mark_in_use(wrapper->var);
}

IMPL_APPENDER(add_var_to_list,
              gcc_variable,
              PyGccVariable_New)


GCC_IMPLEMENT_PUBLIC_API (bool) gcc_variable_get_referring (gcc_variable var,
                    bool (*cb) (gcc_variable var, void *user_data),
                    void *user_data)
{
    ipa_ref *ref = NULL;
    int i;
    for (i = 0; var.inner->iterate_referring(i, ref); i++) {
        if (cb(gcc_private_make_variable((varpool_node*)ref->referring), user_data))
            return true;
    }

    return false;
}

GCC_IMPLEMENT_PUBLIC_API (PyObject *)
PyGccVariable_get_referring(struct PyGccVariable * self)
{
    IMPL_LIST_MAKER(gcc_variable_get_referring,
                    self->var,
                    add_var_to_list)
}


GCC_IMPLEMENT_PUBLIC_API (bool) gcc_variable_get_reference (gcc_variable var,
                    bool (*cb) (gcc_variable var, void *user_data),
                    void *user_data)
{
    ipa_ref *ref = NULL;
    int i;
    for (i = 0; var.inner->iterate_reference(i, ref); i++) {
        if (cb(gcc_private_make_variable((varpool_node*)ref->referred), user_data))
            return true;
    }

    return false;
}

GCC_IMPLEMENT_PUBLIC_API (PyObject *)
PyGccVariable_get_reference(struct PyGccVariable * self)
{
    IMPL_LIST_MAKER(gcc_variable_get_reference,
                    self->var,
                    add_var_to_list)
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
