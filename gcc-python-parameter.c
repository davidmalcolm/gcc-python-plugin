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
  Wrapper for GCC's params.h.
  We specifically wrap "compiler_param" (a typedef to an enum)
  and use this to get at the associated "param_info" struct
*/
PyObject *
gcc_python_make_wrapper_param_num(compiler_param param_num)
{
    struct PyGccParameter *param_obj = NULL;

    param_obj = PyGccWrapper_New(struct PyGccParameter, &gcc_ParameterType);
    if (!param_obj) {
        goto error;
    }

    param_obj->param_num = param_num;

    return (PyObject*)param_obj;

error:
    return NULL;
}

void
wrtp_mark_for_PyGccParameter(PyGccParameter *wrapper)
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
