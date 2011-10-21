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
  the correct region, but the array has only a subrange of explicit initial
  values, with implicit zero initialization, as per K&R 2nd edn, p86.

  This is handled internally using a gcc.Constructor() expression.
*/

extern void __cpychecker_dump(int);

void
test(int i)
{
    /*
      This initialization doesn't list explicit values for all items, leading
      to a gcc.Constructor() for the implicit zero-fill of the others.
    */
    short array[9] = {42};

    __cpychecker_dump(array[0]); /* should be 42 */
    __cpychecker_dump(array[11]); /* should be 0 */

    __cpychecker_dump(i);

    i = (i & 0x7) + 1;
    /* i should now be provably in the range [1-8]: */
    __cpychecker_dump(i);

    /* array[i] should provably be 0: */
    __cpychecker_dump(array[i]);
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
