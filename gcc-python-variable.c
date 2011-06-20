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

PyObject *
gcc_python_make_wrapper_variable(struct varpool_node *node)
{
    struct PyGccVariable *var_obj = NULL;

    if (NULL == node) {
	Py_RETURN_NONE;
    }
  
    var_obj = PyObject_New(struct PyGccVariable, &gcc_VariableType);
    if (!var_obj) {
        goto error;
    }

    var_obj->var = node;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)var_obj;
      
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
