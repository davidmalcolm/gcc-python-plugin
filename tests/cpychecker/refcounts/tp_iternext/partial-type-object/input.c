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

/*
  tp_iternext callbacks are allowed to returns NULL without setting an
  exception.

  Verify that the logic for this doesn't croak on a PyTypeObject that
  doesn't have an initializer for tp_iternext
*/
PyObject *
test(PyObject *obj)
{
    /* The checker ought to report on the lack of an exception: */
    return NULL;
}

static PyTypeObject test_type = {
    /*
      empty initializer; in particular, lacking an initializer
      for tp_iternext
    */
};

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
