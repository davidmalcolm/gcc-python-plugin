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
  Test of compiling a function that's been (correctly) marked as setting
  an exception on a negative return value
*/

#if defined(WITH_CPYCHECKER_NEGATIVE_RESULT_SETS_EXCEPTION_ATTRIBUTE)
  #define CPYCHECKER_NEGATIVE_RESULT_SETS_EXCEPTION() \
     __attribute__((cpychecker_negative_result_sets_exception))
#else
  #define CPYCHECKER_NEGATIVE_RESULT_SETS_EXCEPTION()
  #error (This should have been defined)
#endif

extern int test(int i)
  CPYCHECKER_NEGATIVE_RESULT_SETS_EXCEPTION();

extern int test(int i)
{
    if (i == 42) {
        return 0; /* success */
    } else {
        /* 
           Erroneously, doesn't set an exception on this path,
           despite having been marked as such:
        */
        return -1; /* failure */
    }
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
