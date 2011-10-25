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
  Test of calling a function that's been marked as returning a borrowed
  reference, but incorrectly treating it as returning a new ref
*/

#if defined(WITH_CPYCHECKER_RETURNS_BORROWED_REF_ATTRIBUTE)
  #define CPYCHECKER_RETURNS_BORROWED_REF() \
     __attribute__((cpychecker_returns_borrowed_ref))
#else
  #define CPYCHECKER_RETURNS_BORROWED_REF()
  #error (This should have been defined)
#endif

extern PyObject *foo(void)
  CPYCHECKER_RETURNS_BORROWED_REF();

PyObject *
test(PyObject *self, PyObject *args)
{
    /*
      This code is incorrect: foo() returns a borrowed ref (or NULL), so the
      returned refcount will be one too low:
    */
    PyObject *obj = foo();
    return obj;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
