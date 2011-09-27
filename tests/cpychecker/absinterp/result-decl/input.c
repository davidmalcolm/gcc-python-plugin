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
  Test of returning a struct containing pointers, which seems
  to gimple containing an assignment to a gcc.ResultDecl;
  in the pretty-printed gimple it looks like:
    assign to fields of a tmp value
    <returnval> = tmp
    return <returnval>
  (this seems to only happen if there are 3 or more fields, and at least two
  are pointers; not sure of exact conditions)
*/

struct foo {
    void *x;
    void *y;
    int z;
};

struct foo
test(void *x, void *y, int z)
{
    struct foo result;

    result.x = x;
    result.y = y;
    result.z = z;

    return result;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
