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
  Test of reading from an array where the read might be from outside
  the array bounds
*/

extern void __cpychecker_dump(int);

static char array[12] = {2, 2, 2, 2, 8, 1, 8, 1, 8, 2, 8, 2};

int
test(int i)
{
    __cpychecker_dump(i);

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
