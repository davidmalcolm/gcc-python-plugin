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
  Test of reading and writing simple arrays via pointers
*/
int test_arrays5(void)
{
    int arr[10];
    int *ptr = arr + 3;

    ptr[0] = 1;
    ptr[1] = 2;
    ptr[2] = 3;

    /*
      The analyser ought to be able to figure out that there's a single trace
      with return value 6 (rather than "unknown", or uninitialized data):
    */
    return arr[3] + arr[4] + arr[5];
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
