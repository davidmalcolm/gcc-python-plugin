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
  Test of reading from an array where the read can be proven to be within
  the correct region
*/

extern void __cpychecker_dump(int);

int
test(int i)
{
    char array[12] = {2, 2, 2, 2, 8, 1, 8, 1, 8, 2, 8, 2};
    
    __cpychecker_dump(i);

    if (i < 0) {
        /* Explicit check against lower bound: */
        __cpychecker_dump(i);
        return 0;
    }

    __cpychecker_dump(i);

    if (i >= 12) {
        /* Explicit check against upper bound: */
        __cpychecker_dump(i);
        return 1;
    }

    __cpychecker_dump(i);


    /*
      This read is now provably within the array bounds.

      However, array has been initialized element-by-element.
      We need the checker to be smart enough to know that every element
      that could be accessed is initialized, rather than falling back to
      the default "uninitialized" value for the whole of the array region

      See what the checker is able to determine about 'array[i]'
      It ought to be able to determine that it is the range [1-8], based on
      the initializations of 'array' above:
     */
    __cpychecker_dump(array[i]);
    if (array[i] == 8) {
        /*
          In theory we could also figure out that for this to be the case,
          'i' must be in the range [4-10].  However, the checker doesn't
          do this yet.
        */
        return 2;
    }
    return 3;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
