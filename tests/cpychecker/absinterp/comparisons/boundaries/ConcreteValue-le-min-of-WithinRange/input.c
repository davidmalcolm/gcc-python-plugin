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

const unsigned int j;

int
test(void)
{
    int i = 0;

    /*
      Test of:
         ConcreteValue(0) < WithinRange(0, UINT_MAX)
      Either branch is possible, the actual value of the WithinRange could be:
        (a) == 0 -> FALSE, or could be
        (b) in the subrange [1, UINT_MAX] -> TRUE
    */
    if (i < j) {
        return 1;
    } else {
        return 0;
    }
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
