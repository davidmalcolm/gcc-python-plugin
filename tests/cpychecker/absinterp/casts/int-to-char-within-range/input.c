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
  Test of correctly truncating from an int to a char
*/

extern void __cpychecker_dump(int);

extern int foo(int);

char
test(int i)
{
    char ch;
    int j;

    __cpychecker_dump(i);

    j = foo(i);
    __cpychecker_dump(j);

    /* After this point, j should be known to be in the range [0-15] */
    j = j & 0xf;
    __cpychecker_dump(j);

    /*
       This implicitly truncates from int to char, but the known range ought
       to be preserved within the narrower type, i.e. it ought to know ch is
       in [0-15] rather than [0-255]:
    */
    ch = j;

    /* The return value thus ought to be provably in the range [0-15]: */
    return ch;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
