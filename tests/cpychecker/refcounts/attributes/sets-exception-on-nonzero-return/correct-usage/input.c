/*
   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012 Red Hat, Inc.

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
  Test of compiling a function that (correctly) uses a function that's been
  marked as setting an exception when it returns a negative value.
*/

#if defined(WITH_CPYCHECKER_NEGATIVE_RESULT_SETS_EXCEPTION_ATTRIBUTE)
  #define CPYCHECKER_NEGATIVE_RESULT_SETS_EXCEPTION() \
     __attribute__((cpychecker_negative_result_sets_exception))
#else
  #define CPYCHECKER_NEGATIVE_RESULT_SETS_EXCEPTION()
  #error (This should have been defined)
#endif

extern int foo(void)
  CPYCHECKER_NEGATIVE_RESULT_SETS_EXCEPTION();

PyObject *
test(PyObject *self, PyObject *args)
{
    int i;

    i = foo();
    if (i < 0) {
        /*
          This shouldn't lead to a "returning NULL w/o setting exception"
          error, given that foo() has been marked as setting an exception
          on negative:
        */
        return NULL;
    }
    Py_RETURN_NONE;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
