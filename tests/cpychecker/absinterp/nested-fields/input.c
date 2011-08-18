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
  Test that we can cope with nested structures
*/
struct FooType {
    int i;
};

struct BarType {
    struct FooType foo;
    int j;
};

struct BazType {
    struct BarType bar;
    int k;
};

int test_nested(void)
{
    struct BazType baz;

    baz.bar.foo.i = 10;
    baz.bar.j = 100;
    baz.k = 1000;

    /*
      The analyser ought to be able to figure out that the return value is 1110
    */
    return baz.bar.foo.i + baz.bar.j + baz.k;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
