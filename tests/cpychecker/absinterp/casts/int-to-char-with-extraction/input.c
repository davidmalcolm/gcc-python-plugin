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

extern void __cpychecker_dump(char);

extern int foo(int);

int
test(int i)
{
    char ch;
    int j;

    j = foo(i);

    /* 
       This implicitly truncates from int to char, but the range ought to be
       OK:
    */
    ch = j & 0xff;

    __cpychecker_dump(ch);

    /* and this implicitly expands from char back to int: */
    return ch;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
