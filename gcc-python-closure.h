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

#ifndef INCLUDED__GCC_PYTHON_CLOSURE_H
#define INCLUDED__GCC_PYTHON_CLOSURE_H

struct callback_closure
{
    PyObject *callback;
    PyObject *extraargs;
    PyObject *kwargs;
    enum plugin_event event;
      /* or GCC_PYTHON_PLUGIN_BAD_EVENT if not an event */
};

struct callback_closure *
PyGcc_closure_new_generic(PyObject *callback,
                               PyObject *extraargs,
                               PyObject *kwargs);

struct callback_closure *
PyGcc_Closure_NewForPluginEvent(PyObject *callback,
                                        PyObject *extraargs,
                                        PyObject *kwargs,
                                        enum plugin_event event);

PyObject *
PyGcc_Closure_MakeArgs(struct callback_closure * closure,
                             int add_cfun, PyObject *wrapped_gcc_data);

void
PyGcc_closure_free(struct callback_closure *closure);

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/

#endif /* INCLUDED__GCC_PYTHON_CLOSURE_H */
