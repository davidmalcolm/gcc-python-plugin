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
  Test of compiling a function that's been incorrectly marked as returning
  a borrowed reference, when it in fact returns a new reference
*/

#if defined(WITH_CPYCHECKER_RETURNS_BORROWED_REF_ATTRIBUTE)
  #define CPYCHECKER_RETURNS_BORROWED_REF() \
     __attribute__((cpychecker_returns_borrowed_ref))
#else
  #define CPYCHECKER_RETURNS_BORROWED_REF()
  #error (This should have been defined)
#endif

extern PyObject *test(PyObject *self, PyObject *args)
  CPYCHECKER_RETURNS_BORROWED_REF();

PyObject *
test(PyObject *self, PyObject *args)
{
    /*
      This code returns a new reference, but the function has been marked
      as returning a borrowed reference:
    */
    return PyLong_FromLong(42);
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
