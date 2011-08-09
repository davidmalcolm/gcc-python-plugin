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
   Ensure that we handle the GCC nonnull attribute.
*/
struct coord {
    int x;
    int y;
};

/*
  The checker ought to pick up on the "nonnull" attribute, and thus treat
  "coord_ptr" as being non-NULL, and thus not report a possible read through
  NULL.
*/
int test_function(struct coord *coord_ptr) __attribute__((nonnull));

int test_function(struct coord *coord_ptr)
{
    return coord_ptr->x;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
