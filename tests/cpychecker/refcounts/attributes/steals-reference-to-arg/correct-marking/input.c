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
  Test of compiling a function that's been (correctly) marked as stealing
  a reference
*/

#if defined(WITH_CPYCHECKER_STEALS_REFERENCE_TO_ARG_ATTRIBUTE)
  #define CPYCHECKER_STEALS_REFERENCE_TO_ARG(n) \
    __attribute__((cpychecker_steals_reference_to_arg(n)))
#else
  #define CPYCHECKER_STEALS_REFERENCE_TO_ARG(n)
  #error (This should have been defined)
#endif

extern PyObject *test(PyObject *foo, PyObject *bar)
  CPYCHECKER_STEALS_REFERENCE_TO_ARG(1)
  CPYCHECKER_STEALS_REFERENCE_TO_ARG(2);

PyObject *saved_objA;
PyObject *saved_objB;

PyObject *
test(PyObject *foo, PyObject *bar)
{
    /*
      This code steals references to both of its arguments
    */
    saved_objA = foo;
    saved_objB = bar;

    Py_RETURN_NONE;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
