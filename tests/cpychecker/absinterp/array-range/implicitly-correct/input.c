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
  the array bounds, where the proof requires knowledge of bit operations
*/

extern void __cpychecker_dump(int);

char array[12] = {2, 2, 2, 2, 8, 1, 8, 1, 8, 2, 8, 2};

int
test(int i)
{
    __cpychecker_dump(i);

    /* This ought to constrain i to within [0-255]: */
    i = i & 0xff;
    __cpychecker_dump(i);

    /* and this ought to constrain it to within [0-7]: */
    i = i >> 5;
    __cpychecker_dump(i);

    /* and hence this read is within the array bounds: */
    if (array[i] == 8) {
        return 1;
    }
    return 0;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
