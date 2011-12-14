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
  Verify that the checker doesn't erroneously report leaks for a function
  that calls exit
*/

void
test(PyObject *obj)
{
    PyObject *repr;
    const char *msg;

    repr = PyObject_Repr(obj);
    if (repr) {
        msg = PyString_AsString(repr);
    } else {
        msg = "(repr() failed)";
    }

    fprintf(stderr, "error: %s\n", msg);

    /*
      The checker shouldn't report that "repr" has leaked, as
      the call to exit() makes it irrelevant:
    */
    exit(1);
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
