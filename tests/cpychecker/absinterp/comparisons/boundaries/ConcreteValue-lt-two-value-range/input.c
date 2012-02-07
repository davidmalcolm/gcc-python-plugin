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

int
test(int j)
{
    int i = 0;
    if (j < 0) {
        return 0;
    }
    if (j >= 2) {
        return 1;
    }

    /*
      OK, j should now be WithinRange(0, 1)

      Test of:
         ConcreteValue(0) < WithinRange(0, 1)
      Either branch is possible:
    */
    if (i < j) {
        return 2; /* j should provably be 1 */
    } else {
        return 3; /* j should provably be 0 */
    }
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
